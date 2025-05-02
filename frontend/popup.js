import { drawPieChart } from './perfectPieChart.js';

console.log("Welcome to TimelyAI!");
console.log("🔧 popup.js loaded");

document.addEventListener("DOMContentLoaded", () => {
    /* --------------------------------------------------
     *  🔑 GLOBAL STATE
     * --------------------------------------------------*/
    let userId; // populated once storage returns

    /* --------------------------------------------------
     *  🔗 DOM REFERENCES
     * --------------------------------------------------*/
    const taskList = document.getElementById("taskList");
    const addTaskButton = document.getElementById("showTaskForm");
    const modal = document.getElementById("taskModal");
    const closeButton = document.querySelector(".close");
    const submitTaskButton = document.getElementById("submitTask");
    const generateBtn = document.getElementById("generateRecsBtn");
    const svg = document.getElementById("perfectPie");

    /* --------------------------------------------------
     *  🗝️  LOAD USER ID FROM CHROME STORAGE
     * --------------------------------------------------*/
    chrome.storage.local.get(['userEmail'], (result) => {
        userId = result.userEmail;
        if (!userId) {
            console.error('❌ Could not retrieve userEmail from storage');
            return;
        }

        console.log('✅ Retrieved email:', userId);
        localStorage.setItem('userId', userId);

        // Initial population
        loadTasks(userId);
    });

    /* --------------------------------------------------
     *  📥  FETCH & RENDER TASKS
     * --------------------------------------------------*/
    async function loadTasks(uid = userId) {
        if (!uid) {
            console.warn('loadTasks called before userId is set');
            return;
        }

        taskList.innerHTML = '<li>Loading tasks...</li>';

        try {
            const response = await fetch(`http://localhost:8888/api/tasks?userId=${encodeURIComponent(uid)}`);
            const tasks = await response.json();

            // Category‑duration aggregation for the pie
            const weeklyBreakup = { School: 0, Clubs: 0, Friends: 0, Hobbies: 0, Other: 0 };

            taskList.innerHTML = '';

            if (tasks.length === 0) {
                taskList.innerHTML = '<li>No tasks found.</li>';
                drawPieChart([], svg); // Clear the pie
                return;
            }

            tasks.forEach((task) => {
                const emoji = getCategoryEmoji(task.category || 'Other');
                const li = document.createElement('li');

                // Aggregate durations
                if (!isNaN(task.duration) && task.duration.trim() !== '') {
                    weeklyBreakup[task.category] += parseInt(task.duration, 10);
                }

                li.innerHTML = `
          <strong>${emoji} ${task.title}</strong>
          <span>Due: ${task.dueDate} | Duration: ${task.duration} | Category: ${task.category}</span>
        `;
                li.style.cursor = 'pointer';

                li.addEventListener('click', () => {
                    document.getElementById('taskModalTitle').textContent = task.title;
                    document.getElementById('taskModalDue').textContent = task.dueDate;
                    document.getElementById('taskModalDuration').textContent = task.duration;
                    document.getElementById('taskModalCategory').textContent = task.category;
                    document.getElementById('taskDetailModal').style.display = 'block';
                });

                taskList.appendChild(li);
            });

            /* -------- 🍰 Build slices for pie -------- */
            const total = Object.values(weeklyBreakup).reduce((a, b) => a + b, 0);
            const slices = Object.entries(weeklyBreakup).map(([label, count]) => {
                const percent = total === 0 ? 0 : (count / total) * 100;
                const colorMap = {
                    School: '#3CAE63',
                    Clubs: '#FF9800',
                    Friends: '#2196F3',
                    Hobbies: '#9C27B0',
                    Other: '#607D8B',
                };
                return { percent: +percent.toFixed(1), label, color: colorMap[label] || '#999' };
            });

            /* -------- 🎯 Overlay goals and draw pie -------- */
            try {
                const res = await fetch(`http://localhost:8888/api/goals?userId=${encodeURIComponent(uid)}`);
                const data = await res.json();
                const goals = data.goals || {};
                drawPieChart(slices, svg, goals);
                console.log('✅ Pie chart redrawn with goals overlay');
            } catch (err) {
                console.error('❌ Failed to fetch goals for pie chart:', err);
                drawPieChart(slices, svg); // draw pie without goals overlay
            }

            console.log('✅ Tasks refreshed from backend.');
        } catch (err) {
            console.error('❌ Failed to fetch tasks:', err);
            taskList.innerHTML = '<li>Error loading tasks.</li>';
            drawPieChart([], svg); // Clear chart on error
        }
    }

    /* --------------------------------------------------
     *  🛠️  MODAL BEHAVIOUR
     * --------------------------------------------------*/
    // Task‑detail modal (read‑only)
    document.getElementById('closeTaskDetailModal').addEventListener('click', () => {
        document.getElementById('taskDetailModal').style.display = 'none';
    });

    window.addEventListener('click', (event) => {
        if (event.target === document.getElementById('taskDetailModal')) {
            document.getElementById('taskDetailModal').style.display = 'none';
        }
    });

    // Task‑creation modal (form)
    addTaskButton.addEventListener('click', () => (modal.style.display = 'block'));
    closeButton.addEventListener('click', () => (modal.style.display = 'none'));
    window.addEventListener('click', (event) => {
        if (event.target === modal) modal.style.display = 'none';
    });

    /* --------------------------------------------------
     *  ➕  SUBMIT NEW TASK
     * --------------------------------------------------*/
    submitTaskButton.addEventListener('click', () => {
        if (!userId) {
            alert('User not loaded yet; please wait.');
            return;
        }

        let title = document.getElementById('taskTitle').value.trim() || 'Untitled Task';
        let dueDate = document.getElementById('taskDueDate').value;
        let duration = document.getElementById('taskDuration').value.trim() || 'TBD';
        let category = document.getElementById('taskCategory').value.trim() || 'Other';

        // Re‑format date YYYY‑MM‑DD → M/D/YY
        if (dueDate) {
            const [year, month, day] = dueDate.split('-');
            dueDate = `${parseInt(month, 10)}/${parseInt(day, 10)}/${year.slice(-2)}`;
        } else {
            dueDate = 'TBD';
        }

        const taskDetails = { title, dueDate, duration, category };

        fetch('http://localhost:8888/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId, taskDetails }),
        })
            .then((res) => res.json())
            .then((data) => {
                console.log('✅ Task added:', data);
                loadTasks(userId); // Refresh with correct ID
            })
            .catch((error) => console.error('❌ Error sending task:', error));

        // Reset form + close
        modal.style.display = 'none';
        document.getElementById('taskTitle').value = '';
        document.getElementById('taskDueDate').value = '';
        document.getElementById('taskDuration').value = '';
        document.getElementById('taskCategory').value = 'School';
    });

    /* --------------------------------------------------
     *  💡  RECOMMENDATIONS BUTTON
     * --------------------------------------------------*/
    generateBtn.addEventListener('click', async () => {
        if (!userId) {
            alert('User not loaded yet; please wait.');
            return;
        }

        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';

        try {
            const res = await fetch('http://localhost:8888/api/generate-recs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId }),
            });

            const data = await res.json();

            if (data.status === 'success' && data.showSchedule && data.schedule) {
                // Format schedule for display
                const scheduleText = data.schedule.map(item =>
                    `📅 ${item.title}\n   • Start: ${item.start}\n   • Duration: ${item.duration}`
                ).join('\n\n');

                alert('🎯 Your Schedule:\n\n' + scheduleText);
            } else if (data.status === 'quota_exceeded' && data.showSchedule && data.schedule) {
                // Show schedule even when quota is exceeded
                const scheduleText = data.schedule.map(item =>
                    `📅 ${item.title}\n   • Start: ${item.start}\n   • Duration: ${item.duration}`
                ).join('\n\n');

                alert('⚠️ Calendar quota exceeded, but here\'s your schedule:\n\n' + scheduleText);
            } else if (data.error) {
                alert(data.error);
            } else {
                alert('⚠️ No recommendations could be generated.');
            }
        } catch (err) {
            console.error('❌ Failed to fetch recommendations:', err);
            alert('❌ Error fetching recommendations.');
        } finally {
            generateBtn.disabled = false;
            generateBtn.textContent = 'Get Recommendations';
        }
    });

    /* --------------------------------------------------
     *  🎨  UTILITY – EMOJI MAPPER
     * --------------------------------------------------*/
    function getCategoryEmoji(category) {
        switch (category) {
            case 'School': return '📚';
            case 'Clubs': return '🏀';
            case 'Friends': return '👯‍♀️';
            case 'Hobbies': return '🎨';
            case 'Other': return '💪';
            default: return '✅';
        }
    }
});
