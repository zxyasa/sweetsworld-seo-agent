import { z } from 'zod';

export const postSchema = z.object({
  title: z.string().min(1),
  url: z.string().url(),
  slug: z.string().min(1),
  excerpt: z.string(),
  image: z.string().url().optional(),
});

export function validateInput(post: any) {
  return postSchema.safeParse(post);
}