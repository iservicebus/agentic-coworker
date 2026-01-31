import { getAuthProvidersWithSecrets } from './iam.js';

async function testGetAuthProvidersWithSecrets() {
  console.log('Testing getAuthProvidersWithSecrets...');
  try {
    const providers = await getAuthProvidersWithSecrets('default');
    console.log('Successfully fetched and decrypted auth providers:');
    console.log(JSON.stringify(providers, null, 2));
  } catch (error) {
    console.error('Test failed:', error);
  }
}

testGetAuthProvidersWithSecrets();
