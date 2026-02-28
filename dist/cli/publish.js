"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const commander_1 = require("commander");
const contentGenerator_1 = require("../core/contentGenerator");
const validate_1 = require("../core/validate");
const config_1 = require("../config");
const program = new commander_1.Command();
program
    .name('publish')
    .description('Publish social content for a WordPress post')
    .option('--url <url>', 'WordPress post URL')
    .option('--title <title>', 'Post title')
    .option('--slug <slug>', 'Post slug')
    .option('--excerpt <excerpt>', 'Post excerpt')
    .option('--image <image>', 'Featured image URL')
    .option('--dry-run', 'Dry run mode', false)
    .action(async (options) => {
    const post = {
        title: options.title,
        url: options.url,
        slug: options.slug,
        excerpt: options.excerpt,
        image: options.image,
    };
    const validation = (0, validate_1.validateInput)(post);
    if (!validation.success) {
        console.error('Invalid input:', validation.error);
        process.exit(1);
    }
    const content = (0, contentGenerator_1.generateSocialContent)(validation.data);
    console.log(JSON.stringify(content, null, 2));
    if (!options.dryRun && config_1.config.publishMode === 'live') {
        console.log('Publishing... (not implemented in MVP)');
    }
});
program.parse();
