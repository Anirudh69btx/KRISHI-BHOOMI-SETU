package com.flip.keycloak;

import jakarta.ws.rs.core.Cookie;
import jakarta.ws.rs.core.MultivaluedMap;
import jakarta.ws.rs.core.NewCookie;
import jakarta.ws.rs.core.Response;
import org.keycloak.authentication.AuthenticationFlowContext;
import org.keycloak.authentication.Authenticator;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmModel;
import org.keycloak.models.RoleModel;
import org.keycloak.models.UserModel;
import org.keycloak.models.utils.KeycloakModelUtils;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * Keycloak Authenticator for Farmer Phone + Twilio SMS OTP Authentication.
 * Enhanced with 30-Day "Trusted Device" Remember Me Cookie and Device Fingerprinting.
 */
public class TwilioSmsAuthenticator implements Authenticator {

    private static final Logger logger = Logger.getLogger(TwilioSmsAuthenticator.class.getName());
    private static final String AUTH_NOTE_PHONE = "FLIP_SMS_PHONE";
    private static final String COOKIE_TRUSTED_DEVICE = "flip_trusted_device";
    private static final long TRUSTED_DEVICE_MAX_AGE_SECONDS = 30L * 24 * 60 * 60; // 30 days
    private static final String HMAC_SECRET = System.getenv().getOrDefault("FLIP_COOKIE_SECRET", "flip-trusted-device-secret-key-32chars");

    private static final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();

    private final TwilioConfig twilioConfig;

    public TwilioSmsAuthenticator() {
        this.twilioConfig = TwilioConfig.load();
    }

    @Override
    public void authenticate(AuthenticationFlowContext context) {
        // 1. Check for 30-Day Trusted Device Cookie
        Map<String, Cookie> cookies = context.getHttpRequest().getHttpHeaders().getCookies();
        Cookie trustedCookie = cookies.get(COOKIE_TRUSTED_DEVICE);

        if (trustedCookie != null && isValidTrustedCookie(context, trustedCookie.getValue())) {
            String userPhoneOrSub = extractSubjectFromCookie(trustedCookie.getValue());
            if (userPhoneOrSub != null) {
                UserModel trustedUser = resolveUserByPhoneOrSub(context, userPhoneOrSub);
                if (trustedUser != null) {
                    logger.info("[FLIP-IAM] Valid 30-day trusted device detected for user: " + trustedUser.getUsername() + ". Skipping OTP challenge.");
                    context.setUser(trustedUser);
                    context.success();
                    return;
                }
            }
        }

        // 2. Check if phone is passed in form or query params
        MultivaluedMap<String, String> queryParams = context.getUriInfo().getQueryParameters();
        MultivaluedMap<String, String> formParams = context.getHttpRequest().getDecodedFormParameters();

        String phone = formParams.getFirst("phoneNumber");
        if (phone == null || phone.isBlank()) {
            phone = queryParams.getFirst("phone");
        }

        if (phone == null || phone.isBlank()) {
            context.challenge(renderPhoneForm(context, null));
            return;
        }

        phone = normalizePhone(phone);
        context.getAuthenticationSession().setAuthNote(AUTH_NOTE_PHONE, phone);

        // Send OTP
        boolean sent = sendVerificationCode(phone);
        if (!sent) {
            context.challenge(renderPhoneForm(context, "Failed to send SMS OTP. Please try again."));
            return;
        }

        context.challenge(renderOtpForm(context, phone, null));
    }

    @Override
    public void action(AuthenticationFlowContext context) {
        MultivaluedMap<String, String> formParams = context.getHttpRequest().getDecodedFormParameters();
        String enteredOtp = formParams.getFirst("otp");
        String phone = context.getAuthenticationSession().getAuthNote(AUTH_NOTE_PHONE);
        boolean rememberDevice = "true".equalsIgnoreCase(formParams.getFirst("rememberDevice"))
                || "on".equalsIgnoreCase(formParams.getFirst("rememberDevice"));

        if (formParams.containsKey("resend")) {
            if (phone != null) {
                sendVerificationCode(phone);
                context.challenge(renderOtpForm(context, phone, "New OTP code sent!"));
            } else {
                context.challenge(renderPhoneForm(context, "Session expired. Please re-enter phone."));
            }
            return;
        }

        if (enteredOtp == null || enteredOtp.trim().length() != 6) {
            context.challenge(renderOtpForm(context, phone, "Please enter a valid 6-digit OTP code."));
            return;
        }

        boolean isValid = verifyOtpCode(phone, enteredOtp.trim());
        if (!isValid) {
            context.challenge(renderOtpForm(context, phone, "Invalid OTP code. Please try again."));
            return;
        }

        // OTP Verified successfully! Resolve or create Keycloak user
        UserModel user = resolveOrCreateUser(context, phone);
        context.setUser(user);

        // If "Remember this device" is checked, issue HttpOnly trusted device cookie
        if (rememberDevice) {
            String deviceCookieVal = generateTrustedDeviceToken(context, phone);
            NewCookie cookie = new NewCookie.Builder(COOKIE_TRUSTED_DEVICE)
                    .value(deviceCookieVal)
                    .path("/")
                    .maxAge((int) TRUSTED_DEVICE_MAX_AGE_SECONDS)
                    .secure(false) // Set to true in production HTTPS
                    .httpOnly(true)
                    .sameSite(NewCookie.SameSite.LAX)
                    .build();
            context.getSession().getContext().getHttpResponse().setCookieIfAbsent(cookie);
            logger.info("[FLIP-IAM] 30-Day Trusted Device cookie issued for phone: " + phone);
        }

        context.success();
    }

    private String computeDeviceFingerprint(AuthenticationFlowContext context) {
        try {
            String ua = context.getHttpRequest().getHttpHeaders().getHeaderString("User-Agent");
            String ip = context.getConnection().getRemoteAddr();
            String subnet = ip != null && ip.contains(".") ? ip.substring(0, ip.lastIndexOf(".")) : (ip != null ? ip : "unknown");

            String raw = (ua != null ? ua : "") + "|" + subnet;
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(raw.getBytes(StandardCharsets.UTF_8));
            return Base64.getUrlEncoder().withoutPadding().encodeToString(hash);
        } catch (Exception e) {
            return "default-fingerprint";
        }
    }

    private String generateTrustedDeviceToken(AuthenticationFlowContext context, String phone) {
        try {
            long expiry = Instant.now().getEpochSecond() + TRUSTED_DEVICE_MAX_AGE_SECONDS;
            String fingerprint = computeDeviceFingerprint(context);
            String payload = phone + ":" + expiry + ":" + fingerprint;

            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(HMAC_SECRET.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            String sig = Base64.getUrlEncoder().withoutPadding().encodeToString(mac.doFinal(payload.getBytes(StandardCharsets.UTF_8)));

            return Base64.getUrlEncoder().withoutPadding().encodeToString(payload.getBytes(StandardCharsets.UTF_8)) + "." + sig;
        } catch (Exception e) {
            logger.log(Level.SEVERE, "Failed to generate trusted device token", e);
            return "";
        }
    }

    private boolean isValidTrustedCookie(AuthenticationFlowContext context, String cookieVal) {
        if (cookieVal == null || !cookieVal.contains(".")) return false;
        try {
            String[] parts = cookieVal.split("\\.");
            String payload = new String(Base64.getUrlDecoder().decode(parts[0]), StandardCharsets.UTF_8);
            String sig = parts[1];

            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(HMAC_SECRET.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            String expectedSig = Base64.getUrlEncoder().withoutPadding().encodeToString(mac.doFinal(payload.getBytes(StandardCharsets.UTF_8)));

            if (!expectedSig.equals(sig)) return false;

            String[] fields = payload.split(":");
            long expiry = Long.parseLong(fields[1]);
            if (Instant.now().getEpochSecond() > expiry) return false;

            String cookieFingerprint = fields[2];
            String currentFingerprint = computeDeviceFingerprint(context);
            return cookieFingerprint.equals(currentFingerprint);
        } catch (Exception e) {
            return false;
        }
    }

    private String extractSubjectFromCookie(String cookieVal) {
        try {
            String[] parts = cookieVal.split("\\.");
            String payload = new String(Base64.getUrlDecoder().decode(parts[0]), StandardCharsets.UTF_8);
            return payload.split(":")[0];
        } catch (Exception e) {
            return null;
        }
    }

    private UserModel resolveUserByPhoneOrSub(AuthenticationFlowContext context, String phoneOrSub) {
        RealmModel realm = context.getRealm();
        KeycloakSession session = context.getSession();
        UserModel user = session.users().getUserByUsername(realm, phoneOrSub);
        if (user == null) {
            List<UserModel> users = session.users().searchForUserByUserAttributeStream(realm, "phone", phoneOrSub).toList();
            if (!users.isEmpty()) {
                user = users.get(0);
            }
        }
        return user;
    }

    private UserModel resolveOrCreateUser(AuthenticationFlowContext context, String phone) {
        RealmModel realm = context.getRealm();
        KeycloakSession session = context.getSession();

        UserModel user = resolveUserByPhoneOrSub(context, phone);
        if (user == null) {
            logger.info("[FLIP-IAM] Creating new farmer user for phone: " + phone);
            user = session.users().addUser(realm, KeycloakModelUtils.generateId(), phone, true, true);
            user.setEnabled(true);
            user.setSingleAttribute("phone", phone);
            user.setSingleAttribute("flip_role", "farmer");
            user.setFirstName("Farmer");
            user.setLastName(phone.substring(Math.max(0, phone.length() - 4)));

            RoleModel farmerRole = realm.getRole("farmer");
            if (farmerRole != null) {
                user.grantRole(farmerRole);
            }
        }
        return user;
    }

    private boolean sendVerificationCode(String phone) {
        if (twilioConfig.isMockEnabled()) {
            logger.info("[FLIP-IAM MOCK] SMS OTP sent to " + phone + " => Default OTP: 123456");
            return true;
        }
        try {
            String url = String.format("https://verify.twilio.com/v2/Services/%s/Verifications",
                    twilioConfig.getVerifyServiceSid());
            String body = "To=" + URLEncoder.encode(phone, StandardCharsets.UTF_8) + "&Channel=sms";
            String auth = Base64.getEncoder().encodeToString(
                    (twilioConfig.getAccountSid() + ":" + twilioConfig.getAuthToken()).getBytes(StandardCharsets.UTF_8));
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .header("Authorization", "Basic " + auth)
                    .header("Content-Type", "application/x-www-form-urlencoded")
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            return response.statusCode() == 200 || response.statusCode() == 201;
        } catch (Exception e) {
            logger.log(Level.SEVERE, "[FLIP-IAM] Failed to send Twilio SMS Verify OTP", e);
            return false;
        }
    }

    private boolean verifyOtpCode(String phone, String code) {
        if (twilioConfig.isMockEnabled()) {
            return "123456".equals(code);
        }
        try {
            String url = String.format("https://verify.twilio.com/v2/Services/%s/VerificationCheck",
                    twilioConfig.getVerifyServiceSid());
            String body = "To=" + URLEncoder.encode(phone, StandardCharsets.UTF_8)
                    + "&Code=" + URLEncoder.encode(code, StandardCharsets.UTF_8);
            String auth = Base64.getEncoder().encodeToString(
                    (twilioConfig.getAccountSid() + ":" + twilioConfig.getAuthToken()).getBytes(StandardCharsets.UTF_8));
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .header("Authorization", "Basic " + auth)
                    .header("Content-Type", "application/x-www-form-urlencoded")
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .build();
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            return response.statusCode() == 200 && response.body().contains("\"status\": \"approved\"");
        } catch (Exception e) {
            logger.log(Level.SEVERE, "[FLIP-IAM] Failed to check Twilio OTP", e);
            return false;
        }
    }

    private String normalizePhone(String raw) {
        String digits = raw.replaceAll("[^0-9+]", "");
        if (!digits.startsWith("+")) {
            if (digits.length() == 10) return "+91" + digits;
            return "+" + digits;
        }
        return digits;
    }

    private Response renderPhoneForm(AuthenticationFlowContext context, String error) {
        String actionUrl = context.getActionUrl(context.generateAccessCode()).toString();
        String errorHtml = error != null ? "<div style='color: #ef4444; margin-bottom: 12px; font-weight: 500;'>" + error + "</div>" : "";
        String html = """
            <!DOCTYPE html>
            <html lang='en'>
            <head>
                <meta charset='utf-8'/>
                <meta name='viewport' content='width=device-width, initial-scale=1.0'/>
                <title>FLIP — Farmer Phone Login</title>
                <style>
                    body { margin: 0; font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #064e3b; color: #1f2937; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
                    .card { background: #ffffff; border-radius: 16px; padding: 32px; width: 100%; max-width: 420px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.2); }
                    .title { font-size: 24px; font-weight: 700; color: #065f46; margin-bottom: 8px; }
                    .subtitle { font-size: 14px; color: #6b7280; margin-bottom: 24px; }
                    .input { width: 100%; box-sizing: border-box; padding: 12px 16px; border: 1.5px solid #d1d5db; border-radius: 8px; font-size: 16px; margin-bottom: 16px; }
                    .input:focus { outline: none; border-color: #059669; box-shadow: 0 0 0 3px rgba(5,150,105,0.2); }
                    .btn { width: 100%; background: #059669; color: white; border: none; padding: 12px; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; }
                </style>
            </head>
            <body>
                <div class='card'>
                    <div class='title'>🌾 Krishi Bhoomi Setu</div>
                    <div class='subtitle'>Enter your mobile number to receive a one-time password (OTP)</div>
                    %s
                    <form action='%s' method='post'>
                        <input class='input' type='tel' name='phoneNumber' placeholder='+91 9876543210' required autofocus/>
                        <button class='btn' type='submit'>Send OTP</button>
                    </form>
                </div>
            </body>
            </html>
            """.formatted(errorHtml, actionUrl);

        return Response.ok(html).type("text/html").build();
    }

    private Response renderOtpForm(AuthenticationFlowContext context, String phone, String info) {
        String actionUrl = context.getActionUrl(context.generateAccessCode()).toString();
        String infoHtml = info != null ? "<div style='color: #059669; margin-bottom: 12px; font-weight: 500;'>" + info + "</div>" : "";
        String html = """
            <!DOCTYPE html>
            <html lang='en'>
            <head>
                <meta charset='utf-8'/>
                <meta name='viewport' content='width=device-width, initial-scale=1.0'/>
                <title>FLIP — Enter OTP Code</title>
                <style>
                    body { margin: 0; font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #064e3b; color: #1f2937; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
                    .card { background: #ffffff; border-radius: 16px; padding: 32px; width: 100%; max-width: 420px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.2); }
                    .title { font-size: 24px; font-weight: 700; color: #065f46; margin-bottom: 8px; }
                    .subtitle { font-size: 14px; color: #6b7280; margin-bottom: 24px; }
                    .input { width: 100%; box-sizing: border-box; padding: 14px 16px; border: 1.5px solid #d1d5db; border-radius: 8px; font-size: 24px; letter-spacing: 6px; text-align: center; margin-bottom: 16px; font-weight: bold; }
                    .input:focus { outline: none; border-color: #059669; box-shadow: 0 0 0 3px rgba(5,150,105,0.2); }
                    .btn { width: 100%; background: #059669; color: white; border: none; padding: 12px; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; margin-bottom: 8px; }
                    .checkbox-row { display: flex; align-items: center; gap: 8px; font-size: 14px; color: #4b5563; margin-bottom: 16px; }
                </style>
            </head>
            <body>
                <div class='card'>
                    <div class='title'>🌾 Verify OTP</div>
                    <div class='subtitle'>Sent 6-digit code to <strong>%s</strong></div>
                    %s
                    <form action='%s' method='post'>
                        <input class='input' type='text' name='otp' maxlength='6' pattern='[0-9]{6}' placeholder='123456' required autofocus/>
                        <div class='checkbox-row'>
                            <input type='checkbox' id='rememberDevice' name='rememberDevice' value='true' checked />
                            <label for='rememberDevice'>Remember me on this device (30-day trusted session)</label>
                        </div>
                        <button class='btn' type='submit'>Verify &amp; Continue</button>
                    </form>
                </div>
            </body>
            </html>
            """.formatted(phone, infoHtml, actionUrl);

        return Response.ok(html).type("text/html").build();
    }

    @Override
    public boolean requiresUser() {
        return false;
    }

    @Override
    public boolean configuredFor(KeycloakSession session, RealmModel realm, UserModel user) {
        return true;
    }

    @Override
    public void setRequiredActions(KeycloakSession session, RealmModel realm, UserModel user) {
    }

    @Override
    public void close() {
    }
}

