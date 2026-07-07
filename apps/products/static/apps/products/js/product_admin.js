document.addEventListener('DOMContentLoaded', function () {
    const categoriesSelect = document.getElementById('id_categories');
    const subcategoriesSelect = document.getElementById('id_subcategories');

    if (!categoriesSelect || !subcategoriesSelect) {
        return;
    }

    const pathSegments = window.location.pathname.split('/').filter(Boolean);
    let basePath = window.location.pathname;

    if (pathSegments[pathSegments.length - 1] === 'add') {
        basePath = '/' + pathSegments.slice(0, -1).join('/') + '/';
    } else if (pathSegments[pathSegments.length - 1] === 'change') {
        basePath = '/' + pathSegments.slice(0, -2).join('/') + '/';
    }

    const endpoint = basePath + 'ajax/get-subcategories/';

    function fetchSubcategories() {
        const selectedIds = Array.from(categoriesSelect.selectedOptions)
            .map(option => option.value)
            .filter(Boolean);

        const existingOptions = Array.from(subcategoriesSelect.options).map(option => ({
            value: option.value,
            text: option.textContent || option.text,
            selected: option.selected,
        }));
        const selectedValues = new Set(
            existingOptions.filter(option => option.selected).map(option => String(option.value))
        );

        const url = new URL(endpoint);
        if (selectedIds.length > 0) {
            url.searchParams.set('category_ids', selectedIds.join(','));
        }

        fetch(url.toString(), {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    return;
                }

                subcategoriesSelect.innerHTML = '';

                existingOptions.forEach(option => {
                    const optionEl = document.createElement('option');
                    optionEl.value = option.value;
                    optionEl.text = option.text;
                    optionEl.selected = option.selected;
                    subcategoriesSelect.appendChild(optionEl);
                });

                const existingValues = new Set(existingOptions.map(option => String(option.value)));

                data.subcategories.forEach(subcategory => {
                    const value = String(subcategory.id);
                    if (!existingValues.has(value)) {
                        const option = document.createElement('option');
                        option.value = value;
                        option.text = subcategory.name;
                        if (selectedValues.has(value)) {
                            option.selected = true;
                        }
                        subcategoriesSelect.appendChild(option);
                    } else {
                        const option = Array.from(subcategoriesSelect.options).find(item => String(item.value) === value);
                        if (option) {
                            option.text = subcategory.name;
                            option.selected = selectedValues.has(value);
                        }
                    }
                });

                subcategoriesSelect.dispatchEvent(new Event('change', { bubbles: true }));
            })
            .catch(error => {
                console.error('Error loading subcategories:', error);
            });
    }

    categoriesSelect.addEventListener('change', fetchSubcategories);

    if (categoriesSelect.selectedOptions.length > 0 || subcategoriesSelect.selectedOptions.length > 0) {
        fetchSubcategories();
    }
});
