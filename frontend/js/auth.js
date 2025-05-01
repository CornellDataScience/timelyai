/**
 * Chrome Identity Authentication Module
 * Handles authentication with Google Calendar API using Chrome identity
 */

// Scopes required for Google Calendar API
const SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/calendar.readonly'
];

/**
 * Get an authentication token from Chrome identity
 * @param {boolean} interactive - Whether to show the auth UI if needed
 * @returns {Promise<string>} - The authentication token
 */
function getAuthToken(interactive = true) {
    return new Promise((resolve, reject) => {
        // Use a simpler approach without scopes parameter
        chrome.identity.getAuthToken({
            interactive: interactive
        }, function (token) {
            if (chrome.runtime.lastError) {
                console.error('Auth error:', chrome.runtime.lastError);
                reject(chrome.runtime.lastError);
            } else {
                console.log('Got token:', token);
                resolve(token);
            }
        });
    });
}

/**
 * Remove the authentication token
 * @returns {Promise<void>}
 */
function removeAuthToken() {
    return new Promise((resolve, reject) => {
        chrome.identity.getAuthToken({ interactive: false }, function (token) {
            if (chrome.runtime.lastError) {
                reject(chrome.runtime.lastError);
                return;
            }

            // Remove the token from Chrome's identity API
            chrome.identity.removeCachedAuthToken({ token: token }, function () {
                if (chrome.runtime.lastError) {
                    reject(chrome.runtime.lastError);
                } else {
                    resolve();
                }
            });
        });
    });
}

/**
 * Check if the user is authenticated
 * @returns {Promise<boolean>} - Whether the user is authenticated
 */
function isAuthenticated() {
    return new Promise((resolve) => {
        chrome.identity.getAuthToken({ interactive: false }, function (token) {
            resolve(!!token && !chrome.runtime.lastError);
        });
    });
}

/**
 * Initialize authentication
 * @returns {Promise<void>}
 */
async function initAuth() {
    try {
        // Check if already authenticated
        const authenticated = await isAuthenticated();
        if (authenticated) {
            console.log('Already authenticated');
            return;
        }

        // Get a new token
        const token = await getAuthToken(true);
        console.log('Authentication successful');
        return token;
    } catch (error) {
        console.error('Authentication failed:', error);
        throw error;
    }
}

// Export the functions
window.auth = {
    getAuthToken,
    removeAuthToken,
    isAuthenticated,
    initAuth
}; 