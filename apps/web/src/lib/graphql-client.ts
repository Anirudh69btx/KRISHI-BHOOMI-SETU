/**
 * FLIP v3.0 — GraphQL Client
 * Typed GraphQL client using graphql-request with auth token injection.
 */

import { GraphQLClient } from 'graphql-request';

const GRAPHQL_ENDPOINT = `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/graphql`;

// Singleton GraphQL client
let _client: GraphQLClient | null = null;

export function getGraphQLClient(accessToken?: string | null): GraphQLClient {
  if (!_client) {
    _client = new GraphQLClient(GRAPHQL_ENDPOINT);
  }

  if (accessToken) {
    _client.setHeader('Authorization', `Bearer ${accessToken}`);
  }

  return _client;
}

// ─── Typed Queries ────────────────────────────────────────────────────────────

export const GET_FARMS_QUERY = /* GraphQL */ `
  query GetFarms {
    farms {
      id
      name
      areaHectares
      primaryCrop
      district
      state
      isActive
    }
  }
`;

export const GET_FARM_SENSORS_QUERY = /* GraphQL */ `
  query GetFarmSensors($farmId: UUID!, $hours: Int) {
    sensorReadings(farmId: $farmId, hours: $hours) {
      sensorId
      metric
      value
      unit
      quality
      recordedAt
    }
  }
`;

export const GET_ADVISORIES_QUERY = /* GraphQL */ `
  query GetAdvisories($farmId: UUID!, $unreadOnly: Boolean) {
    advisories(farmId: $farmId, unreadOnly: $unreadOnly) {
      id
      advisoryType
      severity
      title
      body
      confidence
      validFrom
      acknowledgedAt
    }
  }
`;

export const GET_DISASTER_ALERTS_QUERY = /* GraphQL */ `
  query GetDisasterAlerts($district: String, $state: String) {
    disasterAlerts(district: $district, state: $state) {
      id
      alertType
      severity
      title
      description
      affectedDistricts
      issuedAt
      expiresAt
      isDrill
    }
  }
`;

export const ACKNOWLEDGE_ADVISORY_MUTATION = /* GraphQL */ `
  mutation AcknowledgeAdvisory($advisoryId: UUID!) {
    acknowledgeAdvisory(advisoryId: $advisoryId) {
      id
      acknowledgedAt
    }
  }
`;
