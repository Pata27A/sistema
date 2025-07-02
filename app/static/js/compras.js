function initializePurchaseForm() {
    const quantityInput = document.getElementById('quantity');
    const unitPriceInput = document.getElementById('unitPrice');
    const addProductBtn = document.getElementById('addProduct');
    const productsTableBody = document.getElementById('productsTableBody');
    const completePurchaseBtn = document.getElementById('completePurchase');
    const supplierSearch = document.getElementById('supplierSearch');
    const supplierResults = document.getElementById('supplierResults');
    const supplierIdInput = document.getElementById('supplierId');
    const productSearch = document.getElementById('productSearch');
    const productResults = document.getElementById('productResults');

    let products = [];

    function updateTotals() {
        let subtotal = 0, iva5 = 0, iva10 = 0;

        products.forEach(p => {
            subtotal += p.subtotal;
            if (p.iva === '5') iva5 += p.subtotal / 21;
            else if (p.iva === '10') iva10 += p.subtotal / 11;
        });

        const total = subtotal + iva5 + iva10;

        document.getElementById('subtotalDisplay').textContent = formatPYG(subtotal);
        document.getElementById('iva5Display').textContent = formatPYG(Math.round(iva5));
        document.getElementById('iva10Display').textContent = formatPYG(Math.round(iva10));
        document.getElementById('totalDisplay').textContent = formatPYG(total);
    }

    function formatPYG(value) {
        return '₲ ' + value.toLocaleString('es-PY', { maximumFractionDigits: 0 });
    }

    function renderTable() {
        productsTableBody.innerHTML = '';
        products.forEach((p, index) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${p.code}</td>
                <td>${p.name}</td>
                <td>${p.quantity}</td>
                <td>${formatPYG(p.unit_price)}</td>
                <td>${p.iva}%</td>
                <td>${formatPYG(p.subtotal)}</td>
                <td>
                    <button class="btn btn-sm btn-danger" data-index="${index}">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            `;
            productsTableBody.appendChild(tr);
        });

        document.querySelectorAll('#productsTableBody button').forEach(btn => {
            btn.addEventListener('click', function () {
                const index = parseInt(this.dataset.index);
                products.splice(index, 1);
                renderTable();
                updateTotals();
                toggleCompleteButton();
            });
        });

        document.getElementById('emptyProducts').style.display = products.length === 0 ? 'block' : 'none';
    }

    function toggleCompleteButton() {
        const supplierSelected = supplierIdInput.value !== '';
        completePurchaseBtn.disabled = !(products.length > 0 && supplierSelected);
    }

    addProductBtn.addEventListener('click', () => {
        const selectedId = productSearch.dataset.productId;
        const product = {
            id: selectedId,
            code: productSearch.dataset.productCode,
            name: productSearch.dataset.productName,
            unit_price: parseFloat(unitPriceInput.value),
            quantity: parseInt(quantityInput.value),
            iva: productSearch.dataset.productIVA
        };

        if (product.quantity <= 0 || product.unit_price <= 0 || !product.id) {
            alert('Cantidad, precio o producto inválido');
            return;
        }

        product.subtotal = product.unit_price * product.quantity;
        products.push(product);

        renderTable();
        updateTotals();
        toggleCompleteButton();

        productSearch.value = '';
        quantityInput.value = '1';
        unitPriceInput.value = '';
        delete productSearch.dataset.productId;
        delete productSearch.dataset.productCode;
        delete productSearch.dataset.productName;
        delete productSearch.dataset.productIVA;
    });

    completePurchaseBtn.addEventListener('click', async () => {
        const items = products.map(p => ({
            product_id: p.id,
            quantity: p.quantity,
            unit_price: p.unit_price,
            iva: p.iva
        }));

        const data = {
            invoice_number: document.getElementById('invoiceNumber').value,
            supplier_id: supplierIdInput.value,
            notes: document.getElementById('notes').value,
            items: items
        };

        if (!data.invoice_number || !data.supplier_id || items.length === 0) {
            alert('Complete todos los campos obligatorios');
            return;
        }

        try {
            const res = await fetch('/purchases/new', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (res.ok) {
                const responseData = await res.json();
                document.getElementById('completedInvoiceNumber').textContent = responseData.invoice_number || data.invoice_number;
                new bootstrap.Modal(document.getElementById('successModal')).show();

                // Limpieza tras compra exitosa
                products = [];
                renderTable();
                updateTotals();
                toggleCompleteButton();

                supplierSearch.value = '';
                supplierIdInput.value = '';
                document.getElementById('notes').value = '';
                document.getElementById('invoiceNumber').value = '';
            } else {
                const err = await res.json();
                alert(err.message || 'Error al registrar la compra');
            }
        } catch (err) {
            alert('Error al conectar con el servidor');
            console.error(err);
        }
    });

    supplierSearch.addEventListener('input', async function () {
        const term = this.value.trim();
        if (term.length < 2) {
            supplierResults.innerHTML = '';
            return;
        }

        try {
            const res = await fetch(`/api/suppliers/search?q=${encodeURIComponent(term)}`);
            const data = await res.json();
            supplierResults.innerHTML = '';
            data.forEach(supplier => {
                const li = document.createElement('li');
                li.className = 'list-group-item list-group-item-action';
                li.textContent = `${supplier.name} (${supplier.ruc})`;
                li.addEventListener('click', () => {
                    supplierSearch.value = supplier.name;
                    supplierIdInput.value = supplier.id;
                    supplierResults.innerHTML = '';
                    toggleCompleteButton();
                });
                supplierResults.appendChild(li);
            });
        } catch (error) {
            console.error('Error buscando proveedores:', error);
        }
    });

    productSearch.addEventListener('input', async function () {
        const term = this.value.trim();
        if (term.length < 2) {
            productResults.innerHTML = '';
            return;
        }

        try {
            const res = await fetch(`/api/products/search?q=${encodeURIComponent(term)}`);
            const data = await res.json();
            productResults.innerHTML = '';
            data.forEach(product => {
                const li = document.createElement('li');
                li.className = 'list-group-item list-group-item-action';
                li.textContent = `${product.code} - ${product.name}`;
                li.addEventListener('click', () => {
                    productSearch.value = `${product.code} - ${product.name}`;
                    productSearch.dataset.productId = product.id;
                    productSearch.dataset.productCode = product.code;
                    productSearch.dataset.productName = product.name;
                    productSearch.dataset.productIVA = product.iva_type;
                    unitPriceInput.value = product.cost_price;
                    productResults.innerHTML = '';
                });
                productResults.appendChild(li);
            });
        } catch (error) {
            console.error('Error buscando productos:', error);
        }
    });
}

// Esta línea debe ir fuera de la función
document.addEventListener('DOMContentLoaded', () => {
    initializePurchaseForm();
});
