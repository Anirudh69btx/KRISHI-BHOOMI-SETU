import { z } from "zod";

export const UserRoleEnum = z.enum([
  "farmer",
  "fpo_admin",
  "fpo_member",
  "agronomist",
  "gov_officer",
  "buyer",
  "logistics",
  "platform_admin",
  "device",
]);
export type UserRole = z.infer<typeof UserRoleEnum>;

export const OrgTypeEnum = z.enum([
  "FPO",
  "GOVT",
  "BUYER",
  "EXPERT",
  "PARTNER",
  "PLATFORM",
]);
export type OrgType = z.infer<typeof OrgTypeEnum>;

export const OrgSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  type: OrgTypeEnum,
  district_code: z.string().nullable().optional(),
  state_code: z.string().nullable().optional(),
  contact_person: z.string().nullable().optional(),
  contact_phone: z.string().nullable().optional(),
  contact_email: z.string().email().nullable().optional(),
  gst_number: z.string().nullable().optional(),
  fpo_registration_number: z.string().nullable().optional(),
});
export type Org = z.infer<typeof OrgSchema>;

export const UserProfileSchema = z.object({
  id: z.string().uuid(),
  org_id: z.string().uuid().nullable().optional(),
  role: UserRoleEnum.default("farmer"),
  full_name: z.string(),
  phone_number: z.string().nullable().optional(),
  preferred_language: z.enum(["en", "hi"]).default("en"),
  district: z.string().nullable().optional(),
  state: z.string().nullable().optional(),
  avatar_url: z.string().url().nullable().optional(),
  metadata: z.record(z.unknown()).default({}),
});
export type UserProfile = z.infer<typeof UserProfileSchema>;
