const express = require('express');
const cors = require('cors');
const app = express();
const PORT = 4000;

app.use(cors({
  origin: 'chrome-extension://hkjkdbaljlidahhnkjchlpajeddacelh',
  methods: ['GET', 'POST'],
}));

app.use(express.json());

app.get('/api/events', (req, res) => {
  console.log('📥 GET /api/events called');
  const sampleEvents = [
    { id: 1, title: 'Study', time: '10:00 AM' },
    { id: 2, title: 'Gym', time: '5:00 PM' }
  ];
  res.json(sampleEvents);
});

app.post('/api/events', (req, res) => {
  const { userId, eventDetails } = req.body;
  console.log(`Received new event for ${userId}:`, eventDetails);
  res.json({ status: 'success', message: 'Event created!' });
});

app.listen(PORT, () => {
  console.log(`🚀 Backend running on http://localhost:${PORT}`);
});