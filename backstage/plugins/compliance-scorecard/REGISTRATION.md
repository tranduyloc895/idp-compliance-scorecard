# Backstage Plugin Registration Guide

> Run `npx @backstage/create-app@latest` to scaffold Backstage workspace first,
> then merge existing config files and apply the registrations below.

## 1. Register Route in `packages/app/src/App.tsx`

```tsx
// Add import at top
import { CompliancePage } from '@internal/plugin-compliance-scorecard';

// Add inside <FlatRoutes>
<Route path="/compliance" element={<CompliancePage />} />
```

## 2. Add Entity Card in `packages/app/src/components/catalog/EntityPage.tsx`

```tsx
// Add import at top
import { EntityComplianceCard } from '@internal/plugin-compliance-scorecard';

// Add inside serviceEntityPage grid (or defaultEntityPage):
<Grid item md={6}>
  <EntityComplianceCard />
</Grid>
```

## 3. Add Sidebar Item in `packages/app/src/components/Root/Root.tsx`

```tsx
// Add import at top
import SecurityIcon from '@material-ui/icons/Security';

// Add inside <SidebarScrollWrapper> or main sidebar group:
<SidebarItem icon={SecurityIcon} to="compliance" text="Compliance" />
```

## 4. Register Plugin Package

In `packages/app/package.json`, add to dependencies:
```json
"@internal/plugin-compliance-scorecard": "link:../../plugins/compliance-scorecard"
```

Then run:
```bash
yarn install
yarn tsc   # TypeScript compile check
```
