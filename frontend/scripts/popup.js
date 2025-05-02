// DOM Elements
const taskList = document.getElementById('task-list');
const scheduleList = document.getElementById('schedule-list');
const addTaskBtn = document.getElementById('add-task-btn');
const taskModal = document.getElementById('task-modal');
const feedbackModal = document.getElementById('feedback-modal');
const recommendationsModal = document.getElementById('recommendations-modal');
const closeButtons = document.querySelectorAll('.close-modal');
const taskForm = document.getElementById('task-form');
const feedbackForm = document.getElementById('feedback-form');

// State
let currentTask = null;
let currentRecommendations = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadTasks();
    loadSchedule();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    // Modal buttons
    addTaskBtn.addEventListener('click', () => showModal(taskModal));
    closeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            hideAllModals();
        });
    });

    // Forms
    taskForm.addEventListener('submit', handleTaskSubmit);
    feedbackForm.addEventListener('submit', handleFeedbackSubmit);

    // Close modals when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            hideAllModals();
        }
    });
}

// Task Management
async function loadTasks() {
    try {
        const response = await fetch('http://localhost:5000/api/tasks');
        const tasks = await response.json();
        renderTasks(tasks);
    } catch (error) {
        console.error('Error loading tasks:', error);
        showError('Failed to load tasks');
    }
}

function renderTasks(tasks) {
    taskList.innerHTML = '';
    tasks.forEach(task => {
        const taskElement = createTaskElement(task);
        taskList.appendChild(taskElement);
    });
}

function createTaskElement(task) {
    const div = document.createElement('div');
    div.className = 'task-item';
    div.setAttribute('data-task-id', task.id);
    div.innerHTML = `
        <div class="task-info">
            <div class="task-type">${task.type}</div>
            <div class="task-duration">${formatDuration(task.duration)}</div>
            <div class="task-due-date" style="display: none;">${task.dueDate}</div>
        </div>
        <div class="task-actions">
            <button class="secondary-btn" onclick="getRecommendations('${task.id}')">Get Times</button>
            <button class="secondary-btn" onclick="deleteTask('${task.id}')">Delete</button>
        </div>
    `;
    return div;
}

async function handleTaskSubmit(e) {
    e.preventDefault();
    const formData = new FormData(taskForm);
    const task = {
        type: formData.get('task-type'),
        duration: parseFloat(formData.get('duration')),
        dueDate: formData.get('due-date'),
        description: formData.get('description')
    };

    try {
        const response = await fetch('http://localhost:5000/api/tasks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(task)
        });

        if (response.ok) {
            hideAllModals();
            loadTasks();
            taskForm.reset();
        } else {
            throw new Error('Failed to add task');
        }
    } catch (error) {
        console.error('Error adding task:', error);
        showError('Failed to add task');
    }
}

async function deleteTask(taskId) {
    try {
        const response = await fetch(`http://localhost:5000/api/tasks/${taskId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadTasks();
        } else {
            throw new Error('Failed to delete task');
        }
    } catch (error) {
        console.error('Error deleting task:', error);
        showError('Failed to delete task');
    }
}

// Schedule Management
async function loadSchedule() {
    try {
        const response = await fetch('http://localhost:5000/api/schedule');
        const schedule = await response.json();
        renderSchedule(schedule);
    } catch (error) {
        console.error('Error loading schedule:', error);
        showError('Failed to load schedule');
    }
}

function renderSchedule(schedule) {
    scheduleList.innerHTML = '';
    schedule.forEach(item => {
        const scheduleElement = createScheduleElement(item);
        scheduleList.appendChild(scheduleElement);
    });
}

function createScheduleElement(item) {
    const div = document.createElement('div');
    div.className = 'schedule-item';
    div.innerHTML = `
        <span class="time-slot">${formatTime(item.time)}</span>
        <span class="task-type">${item.task}</span>
    `;
    return div;
}

// Recommendations
async function getRecommendations(taskId) {
    try {
        // Get task details from the task list
        const taskElement = document.querySelector(`[data-task-id="${taskId}"]`);
        if (!taskElement) {
            throw new Error('Task not found in UI');
        }

        const taskType = taskElement.querySelector('.task-type').textContent;
        const taskDuration = parseFloat(taskElement.querySelector('.task-duration').textContent);
        const dueDate = taskElement.querySelector('.task-due-date')?.textContent || '';

        // Calculate hours until due
        const hoursUntilDue = dueDate ?
            (new Date(dueDate) - new Date()) / (1000 * 60 * 60) :
            24.0;

        const response = await fetch('http://localhost:5000/api/generate-recs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                userId: localStorage.getItem('userId'), // Make sure this is set during login
                taskId: taskId,
                taskType: taskType,
                taskDuration: taskDuration,
                hoursUntilDue: hoursUntilDue,
                dailyFreeTime: 4.0, // Default value, could be made configurable
                preferSplitting: false // Default value, could be made configurable
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Failed to get recommendations');
        }

        const data = await response.json();
        currentTask = taskId;
        currentRecommendations = data.recommendations;

        showRecommendationsModal(data.recommendations);
    } catch (error) {
        console.error('Error getting recommendations:', error);
        showError('Failed to get recommendations');
    }
}

function showRecommendationsModal(recommendations) {
    const container = document.querySelector('#recommendations-modal .recommendations-container');
    container.innerHTML = '';

    recommendations.forEach((rec, index) => {
        const div = document.createElement('div');
        div.className = 'recommendation-item';
        div.innerHTML = `
            <span>${formatDayAndTime(rec.day, rec.time)}</span>
            <button class="primary-btn" onclick="selectRecommendation(${index})">Select</button>
        `;
        container.appendChild(div);
    });

    showModal(recommendationsModal);
}

function selectRecommendation(index) {
    const recommendation = currentRecommendations[index];
    showFeedbackModal(recommendation);
}

// Feedback
function showFeedbackModal(recommendation) {
    const feedbackContainer = document.querySelector('#feedback-modal .recommendations-container');
    feedbackContainer.innerHTML = `
        <div class="recommendation-item">
            <span>${formatDayAndTime(recommendation.day, recommendation.time)}</span>
        </div>
    `;

    hideModal(recommendationsModal);
    showModal(feedbackModal);
}

async function handleFeedbackSubmit(e) {
    e.preventDefault();
    const formData = new FormData(feedbackForm);
    const feedback = {
        taskId: currentTask,
        time: formData.get('time'),
        day: formData.get('day'),
        rating: parseInt(formData.get('rating')),
        comment: formData.get('comment')
    };

    try {
        const response = await fetch('http://localhost:5000/api/feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(feedback)
        });

        if (response.ok) {
            hideAllModals();
            loadSchedule();
            feedbackForm.reset();
        } else {
            throw new Error('Failed to submit feedback');
        }
    } catch (error) {
        console.error('Error submitting feedback:', error);
        showError('Failed to submit feedback');
    }
}

// Utility Functions
function showModal(modal) {
    modal.style.display = 'block';
}

function hideModal(modal) {
    modal.style.display = 'none';
}

function hideAllModals() {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => hideModal(modal));
}

function showError(message) {
    // TODO: Implement error notification
    console.error(message);
}

function formatDuration(hours) {
    if (hours < 1) {
        return `${Math.round(hours * 60)} minutes`;
    }
    return `${hours} hour${hours === 1 ? '' : 's'}`;
}

function formatTime(time) {
    return new Date(`2000-01-01T${time}`).toLocaleTimeString([], {
        hour: 'numeric',
        minute: '2-digit'
    });
}

function formatDayAndTime(day, time) {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    return `${days[day]} at ${formatTime(time)}`;
} 