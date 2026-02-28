"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.config = void 0;
const dotenv_1 = __importDefault(require("dotenv"));
dotenv_1.default.config();
exports.config = {
    port: parseInt(process.env.PORT || '8787'),
    publishMode: process.env.PUBLISH_MODE || 'dry_run',
    dbPath: process.env.DB_PATH || './data/publish.db',
    baseUrl: process.env.BASE_URL || 'https://sweetsworld.com.au',
    facebook: {
        pageId: process.env.FACEBOOK_PAGE_ID || '',
        accessToken: process.env.FACEBOOK_ACCESS_TOKEN || '',
    },
    instagram: {
        businessId: process.env.INSTAGRAM_BUSINESS_ID || '',
    },
    x: {
        apiKey: process.env.X_API_KEY || '',
        apiSecret: process.env.X_API_SECRET || '',
        accessToken: process.env.X_ACCESS_TOKEN || '',
        accessTokenSecret: process.env.X_ACCESS_TOKEN_SECRET || '',
        bearerToken: process.env.X_BEARER_TOKEN || '', // For read-only operations
    },
    pinterest: {
        accessToken: process.env.PINTEREST_ACCESS_TOKEN || '',
    },
    gbp: {
        accountId: process.env.GBP_ACCOUNT_ID || '',
        locationId: process.env.GBP_LOCATION_ID || '',
        clientId: process.env.GOOGLE_OAUTH_CLIENT_ID || '',
        clientSecret: process.env.GOOGLE_OAUTH_CLIENT_SECRET || '',
        refreshToken: process.env.GOOGLE_OAUTH_REFRESH_TOKEN || '',
    },
    tiktok: {
        clientKey: process.env.TIKTOK_CLIENT_KEY || '',
        clientSecret: process.env.TIKTOK_CLIENT_SECRET || '',
        accessToken: process.env.TIKTOK_ACCESS_TOKEN || '',
    },
    did: {
        apiKey: process.env.DID_API_KEY || '',
    },
};
