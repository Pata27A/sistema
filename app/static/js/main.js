// Main JavaScript file for Ferretería Management System

// Global variables
let salesItems = [];
let purchaseItems = [];

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('es-PY', {
        style: 'currency',
        currency: 'PYG',
        minimumFractionDigits: 0
    }).format(amount).replace('PYG', '₲');
}

function calculateIVA(amount, ivaType) {
    amount = parseFloat(amount);
    if (ivaType === '10') {
        return amount * 0.10;
    } else if (ivaType === '5') {
        return amount * 0.05;
    }
    return 0;
}

function showAlert(message, type = 'info') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    const container = document.querySelector('.container-fluid');
    if (container) {
        container.insertBefore(alertDiv, container.firstChild);
        setTimeout(() => alertDiv.remove(), 5000);
    }
}

function loading(element, show = true) {
    if (show) {
        element.disabled = true;
        element.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Procesando...';
    } else {
        element.disabled = false;
        element.innerHTML = element.dataset.originalText || 'Procesar';
    }
}

// Sales Form
function initializeSaleForm() {
    const invoiceInput = document.getElementById('invoiceNumber');
    if (invoiceInput) {
        fetch('/api/next-invoice-number')
            .then(response => response.json())
            .then(data => {
                invoiceInput.value = data.invoice_number;
            })
            .catch(error => console.error('Error getting invoice number:', error));
    }

    const productSelect = document.getElementById('productSelect');
    const quantityInput = document.getElementById('quantity');
    const addProductBtn = document.getElementById('addProduct');

    if (productSelect && quantityInput && addProductBtn) {
        productSelect.addEventListener('change', function () {
            const selectedOption = this.options[this.selectedIndex];
            if (selectedOption.value) {
                quantityInput.max = selectedOption.dataset.stock;
                quantityInput.disabled = false;
                addProductBtn.disabled = false;
            } else {
                quantityInput.disabled = true;
                addProductBtn.disabled = true;
            }
        });

        addProductBtn.addEventListener('click', function () {
            const productOption = productSelect.options[productSelect.selectedIndex];
            const quantity = parseInt(quantityInput.value);
            if (!productOption.value || quantity <= 0) {
                showAlert('Seleccione un producto y cantidad válida', 'warning');
                return;
            }
            if (quantity > parseInt(productOption.dataset.stock)) {
                showAlert('Cantidad solicitada excede el stock disponible', 'warning');
                return;
            }

            const existingItem = salesItems.find(item => item.product_id === productOption.value);
            if (existingItem) {
                existingItem.quantity += quantity;
                existingItem.subtotal = existingItem.quantity * existingItem.unit_price;
            } else {
                const item = {
                    product_id: productOption.value,
                    code: productOption.dataset.code,
                    name: productOption.dataset.name,
                    quantity: quantity,
                    unit_price: parseFloat(productOption.dataset.price),
                    iva_type: productOption.dataset.iva,
                    subtotal: quantity * parseFloat(productOption.dataset.price)
                };
                salesItems.push(item);
            }

            updateSalesTable();
            updateSalesTotals();

            productSelect.selectedIndex = 0;
            quantityInput.value = 1;
            quantityInput.disabled = true;
            addProductBtn.disabled = true;
        });
    }

    const completeBtn = document.getElementById('completeSale');
    if (completeBtn) {
        completeBtn.addEventListener('click', completeSale);
    }
}

function updateSalesTable() {
    const tbody = document.getElementById('productsTableBody');
    const emptyDiv = document.getElementById('emptyProducts');
    const completeBtn = document.getElementById('completeSale');

    if (!tbody || !emptyDiv || !completeBtn) return;

    if (salesItems.length === 0) {
        tbody.innerHTML = '';
        emptyDiv.style.display = 'block';
        completeBtn.disabled = true;
        return;
    }

    emptyDiv.style.display = 'none';
    completeBtn.disabled = false;

    tbody.innerHTML = salesItems.map((item, index) => `
        <tr>
            <td><code>${item.code}</code></td>
            <td>${item.name}</td>
            <td>${item.quantity}</td>
            <td>${formatCurrency(item.unit_price)}</td>
            <td>
                ${item.iva_type === 'exento'
                    ? '<span class="badge bg-secondary">Exento</span>'
                    : `<span class="badge bg-info">${item.iva_type}%</span>`}
            </td>
            <td>${formatCurrency(item.subtotal)}</td>
            <td>
                <button class="btn btn-sm btn-outline-danger" onclick="removeSalesItem(${index})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function removeSalesItem(index) {
    salesItems.splice(index, 1);
    updateSalesTable();
    updateSalesTotals();
}

function updateSalesTotals() {
    let subtotal = 0;
    let iva5 = 0;
    let iva10 = 0;

    salesItems.forEach(item => {
        subtotal += item.subtotal;
        if (item.iva_type === '5') {
            iva5 += calculateIVA(item.subtotal, '5');
        } else if (item.iva_type === '10') {
            iva10 += calculateIVA(item.subtotal, '10');
        }
    });

    const total = subtotal + iva5 + iva10;

    const subtotalDisplay = document.getElementById('subtotalDisplay');
    const iva5Display = document.getElementById('iva5Display');
    const iva10Display = document.getElementById('iva10Display');
    const totalDisplay = document.getElementById('totalDisplay');

    if (subtotalDisplay) subtotalDisplay.textContent = formatCurrency(subtotal);
    if (iva5Display) iva5Display.textContent = formatCurrency(iva5);
    if (iva10Display) iva10Display.textContent = formatCurrency(iva10);
    if (totalDisplay) totalDisplay.textContent = formatCurrency(total);
}

function completeSale() {
    if (salesItems.length === 0) {
        showAlert('Agregue al menos un producto a la venta', 'warning');
        return;
    }

    const button = document.getElementById('completeSale');
    const invoiceNumber = document.getElementById('invoiceNumber');
    const customerId = document.getElementById('customerId');
    const paymentMethod = document.getElementById('paymentMethod');
    const notes = document.getElementById('notes');
    const csrfToken = document.querySelector('[name=csrf_token]');

    if (!button || !invoiceNumber || !customerId || !paymentMethod || !notes || !csrfToken) return;

    button.dataset.originalText = button.innerHTML;
    loading(button, true);

    const saleData = {
        invoice_number: invoiceNumber.value,
        customer_id: customerId.value || null,
        payment_method: paymentMethod.value,
        notes: notes.value,
        items: salesItems
    };

    fetch('/sales/new', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken.value
        },
        body: JSON.stringify(saleData)
    })
        .then(response => response.json())
        .then(data => {
            loading(button, false);
            if (data.success) {
                document.getElementById('completedInvoiceNumber').textContent = data.invoice_number;
                document.getElementById('printInvoice').onclick = () => {
                    window.open(`/sales/${data.sale_id}/pdf`, '_blank');
                };
                const modal = new bootstrap.Modal(document.getElementById('successModal'));
                modal.show();
                salesItems = [];
                updateSalesTable();
                updateSalesTotals();
            } else {
                showAlert(data.error || 'Error al procesar la venta', 'danger');
            }
        })
        .catch(error => {
            loading(button, false);
            console.error('Error:', error);
            showAlert('Error de conexión', 'danger');
        });
}
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function (e) {
        // Ctrl/Cmd + S para guardar
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            const saveBtn = document.querySelector('button[type="submit"]');
            if (saveBtn) saveBtn.click();
        }

        // Ctrl/Cmd + N para nuevo
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            const newBtn = document.querySelector('a[href*="/new"]');
            if (newBtn) window.location.href = newBtn.href;
        }

        // Escape para cerrar modales
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal.show');
            modals.forEach(modal => {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) bsModal.hide();
            });
        }
    });
}
function initializeTableSorting() {
    document.querySelectorAll('th[data-sort]').forEach(th => {
        th.style.cursor = 'pointer';
        th.addEventListener('click', function () {
            const table = this.closest('table');
            const column = this.dataset.sort;
            const order = this.dataset.order === 'asc' ? 'desc' : 'asc';
            const url = new URL(window.location);
            url.searchParams.set('sort', column);
            url.searchParams.set('order', order);
            window.location.href = url.toString();
        });
    });
}
function initializeSearch() {
    const searchInputs = document.querySelectorAll('input[type="search"]');
    searchInputs.forEach(input => {
        let timeout;
        input.addEventListener('input', function () {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                const form = this.closest('form');
                if (form) {
                    form.submit();
                }
            }, 300);
        });
    });
}
// BÚSQUEDA AUTOMÁTICA EN FORMULARIOS
function initializeSearch() {
    const searchInputs = document.querySelectorAll('input[type="search"]');
    searchInputs.forEach(input => {
        let timeout;
        input.addEventListener('input', function () {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                const form = this.closest('form');
                if (form) form.submit();
            }, 300);
        });
    });
}

// ORDENAMIENTO DE TABLAS
function initializeTableSorting() {
    document.querySelectorAll('th[data-sort]').forEach(th => {
        th.style.cursor = 'pointer';
        th.addEventListener('click', function () {
            const table = this.closest('table');
            const column = this.dataset.sort;
            const order = this.dataset.order === 'asc' ? 'desc' : 'asc';
            const url = new URL(window.location.href);
            url.searchParams.set('sort', column);
            url.searchParams.set('order', order);
            window.location.href = url.toString();
        });
    });
}

// AUTOGUARDADO DE FORMULARIOS
function initializeAutoSave() {
    const forms = document.querySelectorAll('form[data-autosave]');
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('change', function () {
                const formData = new FormData(form);
                localStorage.setItem(`autosave_${form.id}`, JSON.stringify(Object.fromEntries(formData)));
            });
        });
        const savedData = localStorage.getItem(`autosave_${form.id}`);
        if (savedData) {
            const data = JSON.parse(savedData);
            Object.keys(data).forEach(key => {
                const input = form.querySelector(`[name="${key}"]`);
                if (input) input.value = data[key];
            });
        }
    });
}

// ATAJOS DE TECLADO
function initializeKeyboardShortcuts() {
    document.addEventListener('keydown', function (e) {
        // Ctrl/Cmd + S para guardar
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            const saveBtn = document.querySelector('button[type="submit"]');
            if (saveBtn) saveBtn.click();
        }
        // Ctrl/Cmd + N para nuevo
        if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
            e.preventDefault();
            const newBtn = document.querySelector('a[href*="/new"]');
            if (newBtn) window.location.href = newBtn.href;
        }
        // Escape para cerrar modales
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal.show');
            modals.forEach(modal => {
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) bsModal.hide();
            });
        }
    });
}


// Inicialización general
document.addEventListener('DOMContentLoaded', function () {
    const currentPage = window.location.pathname;

    if (currentPage.includes('/sales/new') && document.getElementById('salesForm')) {
        initializeSaleForm();
    }

    // Aquí podés agregar también initializePurchaseForm si lo necesitás
    // if (currentPage.includes('/purchases/new') && document.getElementById('purchaseForm')) {
    //     initializePurchaseForm();
    // }

    initializeKeyboardShortcuts();
    initializeTableSorting();
    initializeSearch();
    initializeAutoSave();

    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(t => new bootstrap.Tooltip(t));

    const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
    popovers.forEach(p => new bootstrap.Popover(p));

    const mainContent = document.querySelector('main');
    if (mainContent) mainContent.classList.add('fade-in');
});

// Global error handler
window.addEventListener('error', function (e) {
    console.error('Global error:', e.error);
    showAlert('Se produjo un error inesperado. Por favor, recargue la página.', 'danger');
});
