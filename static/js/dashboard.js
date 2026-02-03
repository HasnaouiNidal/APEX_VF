// Auto-extracted for dashboard
let timeLeft = 25 * 60; 
    let initialTime = 25; 
    let isRunning = false; 
    let timerInterval; 
    let mode = 'pomodoro';
    
    const modes = {
        'pomodoro': { time: 25, label: 'TIME TO FOCUS' },
        'short': { time: 5, label: 'SHORT BREAK' },
        'long': { time: 50, label: 'DEEP FOCUS' }
    };

    function updateDisplay() {
        let m = Math.floor(timeLeft / 60).toString().padStart(2,'0');
        let s = (timeLeft % 60).toString().padStart(2,'0');
        document.getElementById('timer-display').innerText = `${m}:${s}`;
        
        // SVG Circle Animation
        const circle = document.getElementById('progress-ring');
        const radius = 120;
        const circumference = radius * 2 * Math.PI;
        const totalSeconds = initialTime * 60;
        const offset = circumference - (timeLeft / totalSeconds) * circumference;
        circle.style.strokeDashoffset = offset;
    }

    function setMode(m) { 
        mode = m; 
        initialTime = modes[m].time; 
        timeLeft = initialTime * 60; 
        
        // UI Updates
        document.querySelectorAll('button[id^="btn-"]').forEach(b => b.className = 'px-6 py-2 rounded-lg text-sm font-bold text-gray-500 hover:text-gray-700');
        document.getElementById('btn-'+m).className = 'px-6 py-2 rounded-lg text-sm font-bold bg-white text-indigo-600 shadow-sm';
        document.getElementById('timer-label').innerText = modes[m].label;
        
        updateDisplay(); 
    }

    function toggleTimer() {
        if(isRunning) { 
            clearInterval(timerInterval); 
            document.getElementById('start-btn').innerHTML = '<i class="fa-solid fa-play"></i> <span>Resume</span>'; 
        } else {
            timerInterval = setInterval(() => {
                if(timeLeft > 0) { 
                    timeLeft--; 
                    updateDisplay(); 
                } else { 
                    completeSession(); 
                }
            }, 1000);
            document.getElementById('start-btn').innerHTML = '<i class="fa-solid fa-pause"></i> <span>Pause</span>';
        }
        isRunning = !isRunning;
    }

    function resetTimer() { 
        clearInterval(timerInterval); 
        isRunning = false; 
        setMode(mode); 
        document.getElementById('start-btn').innerHTML = '<i class="fa-solid fa-play"></i> <span>Start Focus</span>';
    }

    function completeSession() {
        clearInterval(timerInterval);
        alert('Session Complete! XP Added.');
        
        // Send data to Flask Backend
        fetch("{{ url_for('save_session') }}", {
            method: 'POST', 
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ duration: initialTime, mode: mode })
        }).then(response => {
            if(response.ok) window.location.reload(); 
        });
    }
    
    updateDisplay();