import {
  createPlugin,
  createRoutableExtension,
} from '@backstage/core-plugin-api';
import { rootRouteRef } from './routes';

export const plugin = createPlugin({
  id: 'compliance-scorecard',
  routes: {
    root: rootRouteRef,
  },
});

export const CompliancePage = plugin.provide(
  createRoutableExtension({
    name: 'CompliancePage',
    component: () =>
      import('./components/CompliancePage/CompliancePage').then(
        m => m.CompliancePage,
      ),
    mountPoint: rootRouteRef,
  }),
);

export const EntityComplianceCard = plugin.provide(
  createRoutableExtension({
    name: 'EntityComplianceCard',
    component: () =>
      import('./components/EntityComplianceCard/EntityComplianceCard').then(
        m => m.EntityComplianceCard,
      ),
    mountPoint: rootRouteRef,
  }),
);
