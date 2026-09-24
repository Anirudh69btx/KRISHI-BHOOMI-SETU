package com.flip.keycloak;

import java.util.logging.Logger;

/**
 * Reads Twilio Verify configuration from Environment variables,
 * Keycloak AuthenticatorConfig, or defaults.
 */
public class TwilioConfig {

    private static final Logger logger = Logger.getLogger(TwilioConfig.class.getName());

    private final String accountSid;
    private final String authToken;
    private final String verifyServiceSid;
    private final boolean mockEnabled;

    public TwilioConfig(String accountSid, String authToken, String verifyServiceSid, boolean mockEnabled) {
        this.accountSid = accountSid;
        this.authToken = authToken;
        this.verifyServiceSid = verifyServiceSid;
        this.mockEnabled = mockEnabled;
    }

    public static TwilioConfig load() {
        String sid = System.getenv("TWILIO_ACCOUNT_SID");
        String token = System.getenv("TWILIO_AUTH_TOKEN");
        String serviceSid = System.getenv("TWILIO_VERIFY_SERVICE_SID");
        String mockEnv = System.getenv("FLIP_OTP_MOCK_ENABLED");

        boolean mock = "true".equalsIgnoreCase(mockEnv) || sid == null || sid.isBlank() || sid.startsWith("AC_MOCK");

        if (mock) {
            logger.info("[FLIP-IAM] TwilioConfig running in MOCK/DEV mode (Any phone + OTP 123456)");
        }

        return new TwilioConfig(
            sid != null ? sid : "AC_MOCK_SID",
            token != null ? token : "MOCK_TOKEN",
            serviceSid != null ? serviceSid : "VA_MOCK_SERVICE_SID",
            mock
        );
    }

    public String getAccountSid() {
        return accountSid;
    }

    public String getAuthToken() {
        return authToken;
    }

    public String getVerifyServiceSid() {
        return verifyServiceSid;
    }

    public boolean isMockEnabled() {
        return mockEnabled;
    }
}
