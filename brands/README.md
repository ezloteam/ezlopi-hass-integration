# Brand assets for home-assistant/brands

Spec-compliant assets for the `ezlopi` domain, generated from the official
ezloPi logo (https://pi.ezlo.com/wp-content/uploads/2022/07/Logo.svg).

| File | Size | Notes |
|------|------|-------|
| `custom_integrations/ezlopi/icon.png` | 256×256 | square "e" monogram, transparent |
| `custom_integrations/ezlopi/icon@2x.png` | 512×512 | hDPI icon |
| `custom_integrations/ezlopi/logo.png` | 256×74 | full wordmark, trimmed, transparent |
| `custom_integrations/ezlopi/logo@2x.png` | 512×149 | hDPI logo |

## Submitting

These go in the [home-assistant/brands](https://github.com/home-assistant/brands)
repo. To submit:

```bash
gh repo fork home-assistant/brands --clone
cd brands
mkdir -p custom_integrations/ezlopi
cp <this-repo>/brands/custom_integrations/ezlopi/*.png custom_integrations/ezlopi/
git checkout -b ezlopi-brand
git add custom_integrations/ezlopi
git commit -m "Add ezlopi brand"
git push -u origin ezlopi-brand
gh pr create --repo home-assistant/brands --title "Add ezlopi brand" \
  --body "Brand assets for the ezloPi custom integration (https://github.com/ezloteam/ezlopi-hass-integration)."
```
