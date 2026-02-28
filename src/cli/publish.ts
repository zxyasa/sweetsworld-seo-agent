import { Command } from 'commander';
import { generateSocialContent } from '../core/contentGenerator';
import { validateInput } from '../core/validate';
import { config } from '../config';

const program = new Command();

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

    const validation = validateInput(post);
    if (!validation.success) {
      console.error('Invalid input:', validation.error);
      process.exit(1);
    }

    const content = generateSocialContent(validation.data);
    console.log(JSON.stringify(content, null, 2));

    if (!options.dryRun && config.publishMode === 'live') {
      console.log('Publishing... (not implemented in MVP)');
    }
  });

program.parse();