# RAY Android mobile app (Sanyam)

This is a **handoff folder, not an implemented Android application**. Sanyam will create the React Native + TypeScript application here, using a compatible Expo Development Build + ViroReact / ARCore stack. Do not generate a separate website.

## Frontend responsibilities
- Sign-in using Supabase Auth; securely pass access token to FastAPI.
- Guide users through material photo, confirmed board dimensions and available space.
- POST authenticated multipart request to `POST /api/v1/reimagine` on the backend.
- Display interactive full `GLB` and individual component `GLB` previews.
- Tap a named component ID and display only matching text instructions/tools/safety guidance.
- Use the same component IDs in the 3D viewer and AR scene; provide 3D-only fallback when AR unavailable.

## API model download detail
**Backend GLB asset endpoints require `Authorization: Bearer <supabase_access_token>`.** Some native model loaders do not let you set arbitrary HTTP headers on their model URLs. If ViroReact's loader cannot pass auth headers, use an authenticated native download to app-private local storage, then point its model source to the saved local file (subject to device/runtime testing). Do not make all designs public to sidestep authentication.

Sample backend-generated contract and GLB assets are under `../backend/examples/`.

When testing on a phone, `localhost` means the **phone**, not Sandeep's laptop. Use a reachable backend URL set in development configuration; do not hardcode a temporary tunnel host or secrets into production code.
