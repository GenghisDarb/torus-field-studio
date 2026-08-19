# Browser performance budget

The browser studio is checked after every production build. Source maps are excluded from the
runtime total.

| Asset class | Uncompressed ceiling |
| --- | ---: |
| All runtime assets | 950 KiB |
| Published example bundles | 4,000 KiB |
| Main JavaScript chunk | 450 KiB |
| Lazy 3D surface chunk | 650 KiB |
| CSS | 120 KiB |

Run `pnpm run build && pnpm run budget` locally. The ceilings are regression guards, not targets;
a change should still justify meaningful growth below the limit. The published-example allowance
retains the immutable v0.2.1 bundle beside the compressed v0.2.2 forensic package. The 3D renderer remains lazy so
the default field view does not pay its parse and execution cost.
