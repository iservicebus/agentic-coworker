import { NextResponse } from 'next/server';
import { generateSampleData } from '@/lib/jsonSchema';

export async function POST(request: Request) {
  console.log('Received request to /api/generate-sample');
  try {
    const schema = await request.json();
    console.log('Received schema:', JSON.stringify(schema, null, 2));

    if (!schema || typeof schema !== 'object' || Object.keys(schema).length === 0) {
      console.log('Schema is empty or invalid.');
      return new NextResponse('JSON schema is empty or invalid', { status: 400 });
    }

    const sampleData = generateSampleData(schema);
    console.log('Generated sample data:', JSON.stringify(sampleData, null, 2));
    return NextResponse.json(sampleData);
  } catch (error: any) {
    console.error('Error in /api/generate-sample:', error);
    return new NextResponse(`Invalid JSON schema: ${error.message}`, { status: 400 });
  }
}
