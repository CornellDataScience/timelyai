const express = require('express');
const cors = require('cors');
const axios = require('axios');
const app = express();
const PORT = 4000;

app.use(cors({
  origin: 'chrome-extension://hkjkdbaljlidahhnkjchlpajeddacelh', // Your Chrome extension's origin
  methods: ['GET', 'POST'],
}));

app.use(express.json());

// ✅ Receive new events
app.post('/api/events', (req, res) => {
    const { userId, eventDetails } = req.body;
    console.log(`📅 Received new event for ${userId}:`, eventDetails);
    res.json({ status: 'success', message: 'Event received' });
});

// ✅ Receive new tasks
app.post('/api/tasks', async (req, res) => {
    const { userId, taskDetails } = req.body;
    console.log(`📝 Received new task for ${userId}:`, taskDetails);
    try {
        // Forward to Python backend
        const response = await axios.post('http://localhost:5000/api/add-task', {
            userId,
            taskDetails
        });
        console.log("✅ Task forwarded to Python backend");
        res.json(response.data);
    } catch (error) {
        console.error('❌ Error forwarding to Python:', error.message);
        res.status(500).json({ status: 'error', message: 'Python backend failed' });
    }
});

// ✅ Deleting tasks (use a different route for deleting tasks)
app.delete('/api/tasks', (req, res) => {
    const { userId, taskId } = req.body;  // Assuming you have taskId for deletion
    console.log(`📝 Deleting task for ${userId}:`, taskId);
    res.json({ status: 'success', message: 'Task Deleted' });
});

// Optional: health check
app.get('/', (req, res) => {
    res.send('TimelyAI backend is running!');
});

app.listen(PORT, () => {
    console.log(`🚀 Backend listening on http://localhost:${PORT}`);
});
