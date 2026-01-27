/**
 * @type {import('@docusaurus/plugin-content-docs').SidebarsConfig}
 */
const sidebars = {
  tutorialSidebar: [
    'intro',
    {
      type: 'category',
      label: 'Getting Started',
      items: [
        'getting-started/installation',
        'getting-started/quickstart',
        'getting-started/configuration',
      ],
    },
    {
      type: 'category',
      label: 'Features',
      items: [
        'features/chat',
        'features/agents',
        'features/documents',
        'features/analytics',
        'features/integrations',
      ],
    },
    {
      type: 'category',
      label: 'Architecture',
      items: [
        'architecture/overview',
        'architecture/backend',
        'architecture/frontend',
        'architecture/database',
        'architecture/security',
      ],
    },
    {
      type: 'category',
      label: 'API Reference',
      items: [
        'api/overview',
        'api/authentication',
        'api/chat',
        'api/agents',
        'api/documents',
        'api/analytics',
      ],
    },
    {
      type: 'category',
      label: 'Deployment',
      items: [
        'deployment/docker',
        'deployment/kubernetes',
        'deployment/terraform',
        'deployment/monitoring',
      ],
    },
    {
      type: 'category',
      label: 'Administration',
      items: [
        'admin/user-management',
        'admin/organization-management',
        'admin/security',
        'admin/monitoring',
      ],
    },
  ],
};

module.exports = sidebars;
