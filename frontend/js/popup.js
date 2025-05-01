/**
 * Popup script for TimelyAI extension
 * Handles UI interactions and authentication flow
 */

document.addEventListener('DOMContentLoaded', async () => {
    // Get UI elements
    const loginButton = document.getElementById('login-button');
    const logoutButton = document.getElementById('logout-button');
    const mainContent = document.getElementById('main-content');

    // Check authentication status on load
    const authenticated = await window.auth.isAuthenticated();
    updateUI(authenticated);

    // Add event listeners
    loginButton.addEventListener('click', handleLogin);
    logoutButton.addEventListener('click', handleLogout);

    /**
     * Handle login button click
     */
    async function handleLogin() {
        try {
            const token = await window.auth.getAuthToken(true);
            console.log('Login successful');
            updateUI(true);
            loadUserData(token);
        } catch (error) {
            console.error('Login failed:', error);
            // Show error message to user
            alert('Failed to sign in. Please try again.');
        }
    }

    /**
     * Handle logout button click
     */
    async function handleLogout() {
        try {
            await window.auth.removeAuthToken();
            console.log('Logout successful');
            updateUI(false);
        } catch (error) {
            console.error('Logout failed:', error);
            alert('Failed to sign out. Please try again.');
        }
    }

    /**
     * Update UI based on authentication status
     * @param {boolean} authenticated - Whether the user is authenticated
     */
    function updateUI(authenticated) {
        if (authenticated) {
            loginButton.style.display = 'none';
            logoutButton.style.display = 'block';
            mainContent.style.display = 'block';
        } else {
            loginButton.style.display = 'block';
            logoutButton.style.display = 'none';
            mainContent.style.display = 'none';
        }
    }

    /**
     * Load user data after authentication
     * @param {string} token - Authentication token
     */
    async function loadUserData(token) {
        try {
            // Load tasks
            const taskList = document.getElementById('task-list');
            taskList.innerHTML = '<p>Loading tasks...</p>';

            // Load schedule
            const schedule = document.getElementById('schedule');
            schedule.innerHTML = '<p>Loading schedule...</p>';

            // Load analytics
            const analytics = document.getElementById('analytics');
            analytics.innerHTML = '<p>Loading analytics...</p>';

            // TODO: Implement API calls to load actual data
            // This is where you'll make requests to your backend

        } catch (error) {
            console.error('Failed to load user data:', error);
            alert('Failed to load your data. Please try again.');
        }
    }
}); 