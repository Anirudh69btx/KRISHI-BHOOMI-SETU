package com.flip.keycloak;

import org.keycloak.Config;
import org.keycloak.authentication.RequiredActionFactory;
import org.keycloak.authentication.RequiredActionProvider;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;

/**
 * Factory for TwilioSmsRequiredAction in Keycloak.
 */
public class TwilioSmsRequiredActionFactory implements RequiredActionFactory {

    @Override
    public String getId() {
        return TwilioSmsRequiredAction.PROVIDER_ID;
    }

    @Override
    public String getDisplayText() {
        return "FLIP Phone SMS Verification";
    }

    @Override
    public RequiredActionProvider create(KeycloakSession session) {
        return new TwilioSmsRequiredAction();
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
