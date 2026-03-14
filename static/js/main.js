// Theme Switcher Logic
document.addEventListener('DOMContentLoaded', () => {
    const themeBtn = document.getElementById('theme-switcher');
    const htmlEl = document.documentElement;
    const darkIcon = document.getElementById('theme-icon-dark');
    const lightIcon = document.getElementById('theme-icon-light');

    // Initialize icons based on current theme from localStorage/FOUC script
    function updateThemeIcon() {
        const currentTheme = htmlEl.getAttribute('data-theme') || 'dark';

        if (currentTheme === 'light') {
            if (darkIcon) darkIcon.classList.remove('d-none');
            if (lightIcon) lightIcon.classList.add('d-none');
        } else {
            if (lightIcon) lightIcon.classList.remove('d-none');
            if (darkIcon) darkIcon.classList.add('d-none');
        }
    }

    if (themeBtn) {
        updateThemeIcon();

        themeBtn.addEventListener('click', () => {
            const currentTheme = htmlEl.getAttribute('data-theme') || 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

            htmlEl.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon();
        });
    }
});
