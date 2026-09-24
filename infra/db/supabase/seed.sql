-- Supabase Specific Seed (Auth Users and Storage Buckets)
INSERT INTO storage.buckets (id, name, public) VALUES 
('flip-models', 'flip-models', false),
('flip-images', 'flip-images', true),
('flip-tiles', 'flip-tiles', true),
('flip-firmware', 'flip-firmware', false),
('flip-assets', 'flip-assets', true)
ON CONFLICT (id) DO NOTHING;
