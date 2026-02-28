#!/usr/bin/env node
/**
 * D-ID Video Generation Test
 * Usage: node test-did-video.js
 */

require('dotenv').config();

async function testDIDVideoGeneration() {
  console.log('🎬 Testing D-ID Video Generation...\n');
  console.log('━'.repeat(60));

  const { DID_API_KEY } = process.env;

  if (!DID_API_KEY) {
    console.log('❌ D-ID API Key not configured');
    console.log('   Add DID_API_KEY to .env file');
    return;
  }

  console.log('✅ D-ID API Key found');
  console.log('   Creating video generation request...\n');

  try {
    // Step 1: Create a talk (video generation task)
    const script = "G'day! Welcome to Sweetsworld, Australia's favourite online candy store. We've got the best chocolate, lollies, and sweet treats!";

    console.log('📝 Script:', script);
    console.log('\n⏳ Sending request to D-ID API...');

    const createResponse = await fetch('https://api.d-id.com/talks', {
      method: 'POST',
      headers: {
        'Authorization': DID_API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        script: {
          type: 'text',
          input: script,
          provider: {
            type: 'microsoft',
            voice_id: 'en-AU-NatashaNeural', // Australian English female voice
          },
        },
        config: {
          fluent: true,
          pad_audio: 0,
        },
        source_url: 'https://d-id-public-bucket.s3.amazonaws.com/alice.jpg',
      }),
    });

    const createData = await createResponse.json();

    if (!createResponse.ok) {
      console.error('\n❌ D-ID API Error:', createData);
      if (createData.kind === 'Unauthorized') {
        console.log('\n💡 Tip: Make sure your API key is correct and includes "Basic " prefix');
      }
      return;
    }

    const videoId = createData.id;
    console.log('✅ Video generation started!');
    console.log('   Video ID:', videoId);
    console.log('\n⏳ Waiting for video generation (this takes 30-60 seconds)...\n');

    // Step 2: Poll for completion
    let attempts = 0;
    const maxAttempts = 60;

    while (attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds

      const statusResponse = await fetch(`https://api.d-id.com/talks/${videoId}`, {
        headers: {
          'Authorization': DID_API_KEY,
        },
      });

      const statusData = await statusResponse.json();
      attempts++;

      if (statusData.status === 'done') {
        console.log('━'.repeat(60));
        console.log('✅ SUCCESS! Video generated!\n');
        console.log('📹 Video URL:', statusData.result_url);
        console.log('⏱️  Generation time:', `~${attempts * 2} seconds`);
        console.log('\n💡 You can download and view this video in your browser');
        console.log('━'.repeat(60));
        return;
      } else if (statusData.status === 'error') {
        console.error('\n❌ Video generation failed:', statusData.error);
        return;
      }

      process.stdout.write(`   Progress: ${attempts}/${maxAttempts} (Status: ${statusData.status})\r`);
    }

    console.log('\n\n⚠️  Video generation timed out after 2 minutes');

  } catch (error) {
    console.error('\n❌ Error:', error.message);
  }
}

testDIDVideoGeneration().catch(console.error);
