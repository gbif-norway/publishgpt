import { parseUploadLimitMB } from './utils/uploadSize.mjs';

const config = {
  baseUrl: process.env.NEXT_PUBLIC_BASE_API_URL || 'http://localhost:8000',
  // Upload limit (in MB) for the UI's pre-checks and messages. The API ingress enforces it, with
  // headroom for multipart overhead (proxy-body-size in the gitops values).
  maxUploadMB: parseUploadLimitMB(process.env.NEXT_PUBLIC_MAX_UPLOAD_MB, 200),
};

export default config;
