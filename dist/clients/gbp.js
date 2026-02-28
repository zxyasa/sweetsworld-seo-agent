"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.postToGBP = postToGBP;
const config_1 = require("../config");
async function postToGBP(summary, cta, link) {
    if (!config_1.config.gbp.accountId) {
        return { status: 'NOT_CONFIGURED' };
    }
    // Placeholder for Google Business Profile API
    return { status: 'SUCCESS', response: { id: 'placeholder' } };
}
