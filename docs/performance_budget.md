# Browser performance budget

The browser studio is checked after every production build. Source maps are excluded from the
runtime total.

| Asset class | Uncompressed ceiling |
| --- | ---: |
| All runtime assets | 1,000 KiB |
| Published example bundles | 6,000 KiB |
| Main JavaScript chunk | 450 KiB |
| Lazy 3D surface chunk | 650 KiB |
| Lazy geometry auditor chunk | 20 KiB |
| CSS | 120 KiB |

Run `pnpm run build && pnpm run budget` locally. The ceilings are regression guards, not targets;
a change should still justify meaningful growth below the limit. The published-example allowance
retains all immutable v0.2 lanes and adds the 2.3 MiB audited v0.3.0 combined geometry bundle. The
geometry auditor and 3D renderer remain lazy so the default field view does not pay their parse
and execution costs.
