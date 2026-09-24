/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_KEYCLOAK_URL?: string;
  readonly VITE_KEYCLOAK_REALM?: string;
  readonly VITE_KEYCLOAK_CLIENT_ID?: string;
  readonly VITE_WS_URL?: string;
  readonly VITE_GRAPHQL_URL?: string;
  readonly VITE_RASA_URL?: string;
  readonly DEV?: boolean;
  readonly PROD?: boolean;
  readonly MODE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
