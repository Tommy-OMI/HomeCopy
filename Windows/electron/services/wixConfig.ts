export const wixConfig = {
  clientId: 'd587c932-f679-4ecb-9eed-646950b99331',
  redirectUri: 'https://www.omiastro.com/_functions/authCallback',
  siteId: '6ce2d899-07f4-421f-912e-872f081db5d9',
  callbackScheme: 'omiastro',
  tokenEndpoint: 'https://www.wixapis.com/oauth2/token',
  redirectSessionEndpoint: 'https://www.wixapis.com/_api/redirects-api/v1/redirect-session',
  currentMemberEndpoint: 'https://www.wixapis.com/members/v1/members/my?fieldsets=FULL',
  licenseActivationEndpoint: 'https://www.omiastro.com/_functions/astera/license/activate'
} as const;

