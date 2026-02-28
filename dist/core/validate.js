"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.postSchema = void 0;
exports.validateInput = validateInput;
const zod_1 = require("zod");
exports.postSchema = zod_1.z.object({
    title: zod_1.z.string().min(1),
    url: zod_1.z.string().url(),
    slug: zod_1.z.string().min(1),
    excerpt: zod_1.z.string(),
    image: zod_1.z.string().url().optional(),
});
function validateInput(post) {
    return exports.postSchema.safeParse(post);
}
