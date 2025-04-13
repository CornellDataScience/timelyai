document.getElementById('fetchEvents').addEventListener('click', async () => {
    const response = await fetch('http://localhost:4000/api/events');
    const data = await response.json();
    
    const output = document.getElementById('output');
    output.innerHTML = '<h3>Events:</h3>' + data.map(event => `
      <div>${event.title} at ${event.time}</div>
    `).join('');
  });
  