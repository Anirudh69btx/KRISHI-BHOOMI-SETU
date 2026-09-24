package com.flip.keycloak;

import jakarta.ws.rs.core.MultivaluedMap;
import jakarta.ws.rs.core.Response;
import org.keycloak.authentication.RequiredActionContext;
import org.keycloak.authentication.RequiredActionProvider;
import org.keycloak.models.UserModel;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Base64;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * Keycloak RequiredAction for Farmer SMS OTP Verification.
 */
public class TwilioSmsRequiredAction implements RequiredActionProvider {

    public static final String PROVIDER_ID = "flip-twilio-sms-action";
    private static final Logger logger = Logger.getLogger(TwilioSmsRequiredAction.class.getName());
    private static final String AUTH_NOTE_PHONE = "FLIP_REQ_PHONE";

    private final TwilioConfig twilioConfig;
    private final HttpClient httpClient;

    public TwilioSmsRequiredAction() {
        this.twilioConfig = TwilioConfig.load();
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(10))
                .build();
    }

    @Override
    public void evaluateTriggers(RequiredActionContext context) {
        UserModel user = context.getUser();
        String phone = user.getFirstAttribute("phone");
        if (phone != null && !Boolean.parseBoolean(user.getFirstAttribute("phone_verified"))) {
            context.getUser().addRequiredAction(PROVIDER_ID);
        }
    }

    @Override
    public void requiredActionChallenge(RequiredActionContext context) {
        UserModel user = context.getUser();
        String phone = user.getFirstAttribute("phone");

        if (phone == null || phone.isBlank()) {
            context.challenge(renderPhoneForm(context, null));
            return;
        }

        context.getAuthenticationSession().setAuthNote(AUTH_NOTE_PHONE, phone);
        sendVerificationCode(phone);
        context.challenge(renderOtpForm(context, phone, null));
    }

    @Override
    public void processAction(RequiredActionContext context) {
        MultivaluedMap<String, String> formParams = context.getHttpRequest().getDecodedFormParameters();
        String phone = context.getAuthenticationSession().getAuthNote(AUTH_NOTE_PHONE);

        if (phone == null) {
            String enteredPhone = formParams.getFirst("phoneNumber");
            if (enteredPhone == null || enteredPhone.isBlank()) {
                context.challenge(renderPhoneForm(context, "Please enter a valid phone number."));
                return;
            }
            phone = normalizePhone(enteredPhone);
            context.getUser().setSingleAttribute("phone", phone);
            context.getAuthenticationSession().setAuthNote(AUTH_NOTE_PHONE, phone);
            sendVerificationCode(phone);
            context.challenge(renderOtpForm(context, phone, null));
            return;
        }

        if (formParams.containsKey("resend")) {
            sendVerificationCode(phone);
            context.challenge(renderOtpForm(context, phone, "New code sent via SMS!"));
            return;
        }

        String otp = formParams.getFirst("otp");
        if (otp == null || otp.trim().length() != 6) {
            context.challenge(renderOtpForm(context, phone, "Enter 6-digit OTP."));
            return;
        }

        boolean valid = verifyOtpCode(phone, otp.trim());
        if (!valid) {
            context.challenge(renderOtpForm(context, phone, "Invalid OTP code. Please try again."));
            return;
        }

        context.getUser().setSingleAttribute("phone_verified", "true");
        context.getUser().removeRequiredAction(PROVIDER_ID);
        context.success();
    }

    private boolean sendVerificationCode(String phone) {
        if (twilioConfig.isMockEnabled()) {
            logger.info("[FLIP-IAM MOCK] RequiredAction OTP sent to " + phone + " => Default OTP: 123456");
            return true;
        }
        try {
            String url = String.format("https://verify.twilio.com/v2/Services/%s/Verifications",
                    twilioConfig.getVerifyServiceSid());
            String body = "To=" + URLEncoder.encode(phone, StandardCharsets.UTF_8) + "&Channel=sms";
            String auth = Base64.getEncoder().encodeToString(
                    (twilioConfig.getAccountSid() + ":" + twilioConfig.getAuthToken()).getBytes(StandardCharsets.UTF_8));
            HttpRequest req = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .header("Authorization", "Basic " + auth)
                    .header("Content-Type", "application/x-www-form-urlencoded")
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .build();
            HttpResponse<String> res = httpClient.send(req, HttpResponse.BodyHandlers.ofString());
            return res.statusCode() == 200 || res.statusCode() == 201;
        } catch (Exception e) {
            logger.log(Level.SEVERE, "[FLIP-IAM] SMS Send Failed", e);
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
            HttpRequest req = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .header("Authorization", "Basic " + auth)
                    .header("Content-Type", "application/x-www-form-urlencoded")
                    .POST(HttpRequest.BodyPublishers.ofString(body))
                    .build();
            HttpResponse<String> res = httpClient.send(req, HttpResponse.BodyHandlers.ofString());
            return res.statusCode() == 200 && res.body().contains("\"status\": \"approved\"");
        } catch (Exception e) {
            logger.log(Level.SEVERE, "[FLIP-IAM] SMS Verify Failed", e);
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

    private Response renderPhoneForm(RequiredActionContext context, String error) {
        String actionUrl = context.getActionUrl().toString();
        String errorHtml = error != null ? "<div style='color: #ef4444; margin-bottom: 12px; font-weight: 500;'>" + error + "</div>" : "";
        String html = """
            <!DOCTYPE html>
            <html lang='en'>
            <head>
                <meta charset='utf-8'/>
                <meta name='viewport' content='width=device-width, initial-scale=1.0'/>
                <title>FLIP — Mobile Verification</title>
                <style>
                    body { margin: 0; font-family: system-ui, -apple-system, sans-serif; background: #064e3b; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
                    .card { background: #ffffff; border-radius: 16px; padding: 32px; width: 100%; max-width: 420px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.2); }
                    .title { font-size: 24px; font-weight: 700; color: #065f46; margin-bottom: 8px; }
                    .subtitle { font-size: 14px; color: #6b7280; margin-bottom: 24px; }
                    .input { width: 100%; box-sizing: border-box; padding: 12px 16px; border: 1.5px solid #d1d5db; border-radius: 8px; font-size: 16px; margin-bottom: 16px; }
                    .btn { width: 100%; background: #059669; color: white; border: none; padding: 12px; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; }
                </style>
            </head>
            <body>
                <div class='card'>
                    <div class='title'>🌾 Phone Verification</div>
                    <div class='subtitle'>Verify your mobile phone to complete setup.</div>
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

    private Response renderOtpForm(RequiredActionContext context, String phone, String info) {
        String actionUrl = context.getActionUrl().toString();
        String infoHtml = info != null ? "<div style='color: #059669; margin-bottom: 12px; font-weight: 500;'>" + info + "</div>" : "";
        String html = """
            <!DOCTYPE html>
            <html lang='en'>
            <head>
                <meta charset='utf-8'/>
                <meta name='viewport' content='width=device-width, initial-scale=1.0'/>
                <title>FLIP — Enter OTP Code</title>
                <style>
                    body { margin: 0; font-family: system-ui, -apple-system, sans-serif; background: #064e3b; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
                    .card { background: #ffffff; border-radius: 16px; padding: 32px; width: 100%; max-width: 420px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.2); }
                    .title { font-size: 24px; font-weight: 700; color: #065f46; margin-bottom: 8px; }
                    .subtitle { font-size: 14px; color: #6b7280; margin-bottom: 24px; }
                    .input { width: 100%; box-sizing: border-box; padding: 14px 16px; border: 1.5px solid #d1d5db; border-radius: 8px; font-size: 24px; letter-spacing: 6px; text-align: center; margin-bottom: 16px; font-weight: bold; }
                    .btn { width: 100%; background: #059669; color: white; border: none; padding: 12px; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; }
                </style>
            </head>
            <body>
                <div class='card'>
                    <div class='title'>🌾 Enter SMS OTP</div>
                    <div class='subtitle'>Verification code sent to <strong>%s</strong></div>
                    %s
                    <form action='%s' method='post'>
                        <input class='input' type='text' name='otp' maxlength='6' pattern='[0-9]{6}' placeholder='123456' required autofocus/>
                        <button class='btn' type='submit'>Verify</button>
                    </form>
                </div>
            </body>
            </html>
            """.formatted(phone, infoHtml, actionUrl);

        return Response.ok(html).type("text/html").build();
    }

    @Override
    public void close() {
    }
}
