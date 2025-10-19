import { json, type LoaderFunctionArgs } from '@remix-run/cloudflare';
import { useLoaderData } from '@remix-run/react';

export async function loader(args: LoaderFunctionArgs) {
  console.log('🧪 TEST route loader called with params:', args.params);
  return json({ testParam: args.params.param, message: 'Test route working!' });
}

export default function TestRoute() {
  const data = useLoaderData<typeof loader>();

  return (
    <div style={{ padding: '20px', backgroundColor: '#e0ffe0' }}>
      <h1>TEST ROUTE WORKING!</h1>
      <h2>Param: {data.testParam}</h2>
      <p>This proves parameterized routes work</p>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}
