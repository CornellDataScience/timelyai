const express = require('express');
const cors = require('cors');
const axios = require('axios');
const app = express();
const PORT = 4000;

app.use(cors({
    origin: 'chrome-extension://hkjkdbaljlidahhnkjchlpajeddacelh', // Your Chrome extension's origin
    methods: ['GET', 'POST', 'DELETE'],
}));

app.use(express.json());

// ✅ Receive new events
app.post('/api/events', (req, res) => {
    const { userId, eventDetails } = req.body;
    console.log(`📅 Received new event for ${userId}:`, eventDetails);
    res.json({ status: 'success', message: 'Event received' });
});

// ✅ Add OR edit tasks (handles both new + edit)
app.post('/api/tasks', async (req, res) => {
    const { userId, taskDetails, taskId } = req.body;
    console.log(`📝 Received ${taskId ? "edit" : "new"} task for ${userId}`);

    try {
        // Forward to Python backend
        const response = await axios.post('http://localhost:8888/api/tasks', {
            userId,
            taskDetails,
            ...(taskId && { taskId })  // ✅ Only attach if editing
        });
        console.log("✅ Task forwarded to Python backend");
        res.json(response.data);
    } catch (error) {
        console.error('❌ Error forwarding to Python:', error.message);
        res.status(500).json({ status: 'error', message: 'Python backend failed' });
    }
});

// ✅ Delete tasks (REAL delete now)
app.delete('/api/tasks', async (req, res) => {
    const { userId, taskId } = req.body;
    console.log(`🗑️ Deleting task for ${userId}: ${taskId}`);

    try {
        const response = await axios.delete('http://localhost:8888/api/delete-task', {
            data: { userId, taskId }  // Axios requires `data` for DELETE
        });
        console.log("✅ Task delete forwarded to Python backend");
        res.json(response.data);
    } catch (error) {
        console.error('❌ Error deleting task:', error.message);
        res.status(500).json({ status: 'error', message: 'Delete failed' });
    }
});

// Optional: health check
app.get('/', (req, res) => {
    res.send('TimelyAI backend is running!');
});

app.listen(PORT, () => {
    console.log(`🚀 Backend listening on http://localhost:${PORT}`);
});
