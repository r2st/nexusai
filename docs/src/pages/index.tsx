import React, { useEffect } from 'react';
import Layout from '@theme/Layout';
import { useHistory } from '@docusaurus/router';

export default function Home(): JSX.Element {
  const history = useHistory();

  useEffect(() => {
    history.replace('/docs/');
  }, [history]);

  return (
    <Layout title="NexusAI Documentation" description="NexusAI documentation home">
      <main style={{ padding: '2rem' }}>
        <h1>NexusAI Documentation</h1>
        <p>
          Redirecting to the docs… If you are not redirected, open <a href="/docs/">/docs/</a>.
        </p>
      </main>
    </Layout>
  );
}

