/**
 * API Service for TimelyAI
 * 
 * This file contains functions to interact with the backend API.
 */

// TimelyAPI - Service for handling all API calls to the backend
const TimelyAPI = {
    // Base URL for API calls
    baseUrl: 'http://localhost:5000/api',

    // User ID (should be set when user logs in)
    userId: null,

    // Set the user ID
    setUserId(id) {
        this.userId = id;
    },

    // Get user preferences
    async getUserPreferences() {
        const response = await fetch(`${this.baseUrl}/user/preferences?userId=${this.userId}`);
        if (!response.ok) {
            throw new Error('Failed to get user preferences');
        }
        return await response.json();
    },

    // Get user tasks
    async getUserTasks() {
        const response = await fetch(`${this.baseUrl}/user/tasks?userId=${this.userId}`);
        if (!response.ok) {
            throw new Error('Failed to get user tasks');
        }
        return await response.json();
    },

    // Get user events
    async getUserEvents() {
        const response = await fetch(`${this.baseUrl}/user/events?userId=${this.userId}`);
        if (!response.ok) {
            throw new Error('Failed to get user events');
        }
        return await response.json();
    },

    // Get user blocked times
    async getUserBlockedTimes() {
        const response = await fetch(`${this.baseUrl}/user/blocked-times?userId=${this.userId}`);
        if (!response.ok) {
            throw new Error('Failed to get user blocked times');
        }
        return await response.json();
    },

    // Get time recommendations for a task
    async getTimeRecommendations(taskData) {
        const response = await fetch(`${this.baseUrl}/recommendations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                userId: this.userId,
                taskType: taskData.type,
                taskDuration: taskData.duration,
                hoursUntilDue: this.calculateHoursUntilDue(taskData.dueDate),
                dailyFreeTime: 8, // Default value, should be calculated based on user's schedule
                dayOfWeek: this.getDayOfWeek(),
                preferSplitting: taskData.preferSplitting
            })
        });

        if (!response.ok) {
            throw new Error('Failed to get time recommendations');
        }

        return await response.json();
    },

    // Record feedback for a recommendation
    async recordRecommendationFeedback(data) {
        const response = await fetch(`${this.baseUrl}/feedback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                userId: this.userId,
                taskData: data.taskData,
                recommendations: data.recommendations,
                wasAccepted: data.wasAccepted
            })
        });

        if (!response.ok) {
            throw new Error('Failed to record feedback');
        }

        return await response.json();
    },

    // Helper function to calculate hours until due
    calculateHoursUntilDue(dueDate) {
        const due = new Date(dueDate);
        const now = new Date();
        const diffMs = due - now;
        return Math.max(0, Math.floor(diffMs / (1000 * 60 * 60)));
    },

    // Helper function to get current day of week
    getDayOfWeek() {
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        return days[new Date().getDay()];
    }
};

// Export the API service functions
window.TimelyAPI = TimelyAPI; 