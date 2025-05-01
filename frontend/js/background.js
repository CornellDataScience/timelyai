/**
 * Background script for TimelyAI extension
 * Handles authentication and API requests
 */

// Listen for installation
chrome.runtime.onInstalled.addListener(() => {
    console.log('TimelyAI extension installed');
});

// Listen for messages from content scripts or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getAuthToken') {
        // Get auth token - simplified approach
        chrome.identity.getAuthToken({ interactive: true }, function (token) {
            if (chrome.runtime.lastError) {
                console.error('Auth error:', chrome.runtime.lastError);
                sendResponse({ error: chrome.runtime.lastError });
            } else {
                console.log('Got token:', token);
                sendResponse({ token: token });
            }
        });
        return true; // Will respond asynchronously
    }

    if (request.action === 'removeAuthToken') {
        // Remove auth token
        chrome.identity.getAuthToken({ interactive: false }, function (token) {
            if (chrome.runtime.lastError) {
                sendResponse({ error: chrome.runtime.lastError });
                return;
            }

            chrome.identity.removeCachedAuthToken({ token: token }, function () {
                if (chrome.runtime.lastError) {
                    sendResponse({ error: chrome.runtime.lastError });
                } else {
                    sendResponse({ success: true });
                }
            });
        });
        return true; // Will respond asynchronously
    }

    if (request.action === 'isAuthenticated') {
        // Check if authenticated
        chrome.identity.getAuthToken({ interactive: false }, function (token) {
            sendResponse({ authenticated: !!token && !chrome.runtime.lastError });
        });
        return true; // Will respond asynchronously
    }
}); 