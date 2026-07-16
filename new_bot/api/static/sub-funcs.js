const detailsList = document.querySelectorAll('details');

detailsList.forEach((details) => {
    details.addEventListener('toggle', (e) => {
        // Проверяем, что текущий тег открылся (а не закрылся)
        if (details.open) {
            // Закрываем все остальные теги details
            detailsList.forEach((otherDetails) => {
                if (otherDetails !== details) {
                    otherDetails.removeAttribute('open');
                }
            });
        }
    });
});