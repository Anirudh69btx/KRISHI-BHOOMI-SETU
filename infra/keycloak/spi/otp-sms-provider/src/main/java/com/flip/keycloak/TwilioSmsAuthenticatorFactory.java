package com.flip.keycloak;

import org.keycloak.Config;
import org.keycloak.authentication.Authenticator;
import org.keycloak.authentication.AuthenticatorFactory;
import org.keycloak.models.AuthenticationExecutionModel;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;
import org.keycloak.provider.ProviderConfigProperty;

import java.util.ArrayList;
import java.util.List;

/**
 * Factory for TwilioSmsAuthenticator SPI in Keycloak.
 */
public class TwilioSmsAuthenticatorFactory implements AuthenticatorFactory {

    public static final String PROVIDER_ID = "flip-twilio-sms-authenticator";

    private static final AuthenticationExecutionModel.Requirement[] REQUIREMENT_CHOICES = {
            AuthenticationExecutionModel.Requirement.REQUIRED,
            AuthenticationExecutionModel.Requirement.ALTERNATIVE,
            AuthenticationExecutionModel.Requirement.DISABLED
    };

    @Override
    public String getId() {
        return PROVIDER_ID;
    }

    @Override
    public String getDisplayType() {
        return "FLIP Twilio SMS OTP Authentication";
    }

    @Override
    public String getHelpText() {
        return "Prompts user for phone number and verifies SMS OTP via Twilio Verify API (or Dev Mock).";
    }

    @Override
    public String getReferenceCategory() {
        return "otp";
    }

    @Override
    public boolean isConfigurable() {
        return true;
    }

    @Override
    public AuthenticationExecutionModel.Requirement[] getRequirementChoices() {
        return REQUIREMENT_CHOICES;
    }

    @Override
    public boolean isUserSetupAllowed() {
        return false;
    }

    @Override
    public List<ProviderConfigProperty> getConfigProperties() {
        List<ProviderConfigProperty> configProperties = new ArrayList<>();

        ProviderConfigProperty mockProperty = new ProviderConfigProperty();
        mockProperty.setName("mockEnabled");
        mockProperty.setLabel("Enable Mock Mode");
        mockProperty.setType(ProviderConfigProperty.BOOLEAN_TYPE);
        mockProperty.setHelpText("If enabled, any phone number can log in with OTP 123456.");
        mockProperty.setDefaultValue("true");
        configProperties.add(mockProperty);

        return configProperties;
    }

    @Override
    public Authenticator create(KeycloakSession session) {
        return new TwilioSmsAuthenticator();
    }

    @Override
    public void init(Config.Scope config) {
    }

    @Override
    public void postInit(KeycloakSessionFactory factory) {
    }

    @Override
    public void close() {
    }
}
