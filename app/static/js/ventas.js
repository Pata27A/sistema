document.addEventListener('DOMContentLoaded', () => {
  const invoiceNumberInput = document.getElementById('invoiceNumber');
  const customerRucInput = document.getElementById('customerRuc');
  const customerNameDisplay = document.getElementById('customerName');
  const customerIdHidden = document.getElementById('customerId');

  const productSearchInput = document.getElementById('productSearch');
  const quantityInput = document.getElementById('quantity');
  const addProductBtn = document.getElementById('addProduct');
  const productsTableBody = document.getElementById('productsTableBody');
  const emptyProductsDiv = document.getElementById('emptyProducts');

  const subtotalDisplay = document.getElementById('subtotalDisplay');
  const iva5Display = document.getElementById('iva5Display');
  const iva10Display = document.getElementById('iva10Display');
  const totalDisplay = document.getElementById('totalDisplay');

  const paymentCashInput = document.getElementById('paymentCash');
  const paymentCardInput = document.getElementById('paymentCard');
  const paymentDifferenceInput = document.getElementById('paymentDifference');
  const completeSaleBtn = document.getElementById('completeSale');

  const notesInput = document.getElementById('notes');
  const successModal = new bootstrap.Modal(document.getElementById('successModal'));
  const completedInvoiceNumberSpan = document.getElementById('completedInvoiceNumber');
  const completedSaleIdSpan = document.getElementById('completedSaleId'); // <p hidden id="completedSaleId"></p>
  const modalChangeSpan = document.getElementById('modalChangeDisplay');

  if (!window.products) window.products = [];
  const saleItems = [];

  fetch('/api/next-invoice-number')
    .then(res => res.json())
    .then(data => {
      invoiceNumberInput.value = data.invoice_number || '001-001-0000001';
    })
    .catch(() => {
      invoiceNumberInput.value = '001-001-0000001';
    });

  let searchTimeout;
  customerRucInput.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    const ruc = customerRucInput.value.trim();
    if (ruc.length < 3) {
      customerNameDisplay.textContent = '';
      customerIdHidden.value = '';
      return;
    }
    searchTimeout = setTimeout(() => {
      fetch(`/api/clientes?ruc=${encodeURIComponent(ruc)}`)
        .then(res => {
          if (!res.ok) throw new Error('Cliente no encontrado');
          return res.json();
        })
        .then(data => {
          customerNameDisplay.textContent = data.name || '';
          customerIdHidden.value = data.id || '';
        })
        .catch(() => {
          customerNameDisplay.textContent = 'Cliente no encontrado';
          customerIdHidden.value = '';
        });
    }, 500);
  });

  addProductBtn.addEventListener('click', () => {
    const search = productSearchInput.value.trim().toLowerCase();
    const quantity = parseInt(quantityInput.value);
    if (!search) return alert('Por favor, busca un producto por código o nombre.');
    if (quantity <= 0) return alert('La cantidad debe ser mayor que cero.');

    const product = window.products.find(p =>
      p.code.toLowerCase() === search || p.name.toLowerCase() === search
    );
    if (!product) return alert('Producto no encontrado.');
    if (product.stock_current < quantity) return alert('No hay suficiente stock para este producto.');

    const existingIndex = saleItems.findIndex(i => i.product_id === product.id);
    if (existingIndex >= 0) {
      saleItems[existingIndex].quantity += quantity;
      saleItems[existingIndex].subtotal = saleItems[existingIndex].quantity * saleItems[existingIndex].unit_price;
    } else {
      saleItems.push({
        product_id: product.id,
        code: product.code,
        name: product.name,
        quantity: quantity,
        unit_price: parseFloat(product.sale_price),
        subtotal: quantity * parseFloat(product.sale_price),
        iva_type: product.iva_type
      });
    }

    productSearchInput.value = '';
    quantityInput.value = 1;
    renderProductsTable();
    updateCompleteButtonState();
  });

  function renderProductsTable() {
    productsTableBody.innerHTML = '';
    if (saleItems.length === 0) {
      emptyProductsDiv.style.display = 'block';
      completeSaleBtn.disabled = true;
      updateTotals();
      return;
    }
    emptyProductsDiv.style.display = 'none';

    saleItems.forEach((item, index) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${item.code}</td>
        <td>${item.name}</td>
        <td>${item.quantity}</td>
        <td>${formatCurrency(item.unit_price)}</td>
        <td>${item.iva_type}%</td>
        <td>${formatCurrency(item.subtotal)}</td>
        <td>
          <button class="btn btn-sm btn-danger btn-remove" data-index="${index}">
            <i class="fas fa-trash"></i>
          </button>
        </td>
      `;
      productsTableBody.appendChild(tr);
    });

    document.querySelectorAll('.btn-remove').forEach(btn => {
      btn.addEventListener('click', e => {
        const idx = parseInt(e.currentTarget.dataset.index);
        saleItems.splice(idx, 1);
        renderProductsTable();
        updateCompleteButtonState();
      });
    });

    updateTotals();
  }

  function updateTotals() {
    let subtotal = 0, iva5 = 0, iva10 = 0;

    saleItems.forEach(item => {
      subtotal += item.subtotal;
      if (item.iva_type === '5') iva5 += item.subtotal / 21;
      else if (item.iva_type === '10') iva10 += item.subtotal / 11;
    });

    const total = subtotal;

    subtotalDisplay.textContent = formatCurrency(subtotal);
    iva5Display.textContent = formatCurrency(Math.round(iva5));
    iva10Display.textContent = formatCurrency(Math.round(iva10));
    totalDisplay.textContent = formatCurrency(total);
    updateDifferenceDisplay(total);
    return total;
  }

  function updateDifferenceDisplay(total) {
    const cash = parseFloat(paymentCashInput.value) || 0;
    const card = parseFloat(paymentCardInput.value) || 0;
    const paid = cash + card;
    const difference = paid - total;
    const change = difference > 0 ? difference : 0;

    if (paymentDifferenceInput) {
      paymentDifferenceInput.value = formatCurrency(difference);
      paymentDifferenceInput.classList.remove('text-danger', 'text-success', 'text-muted');
      if (difference > 0) paymentDifferenceInput.classList.add('text-success');
      else if (difference < 0) paymentDifferenceInput.classList.add('text-danger');
      else paymentDifferenceInput.classList.add('text-muted');
    }
    if (modalChangeSpan) modalChangeSpan.textContent = formatCurrency(change);
  }

  function formatCurrency(value) {
    return `₲ ${value.toLocaleString('es-PY', { minimumFractionDigits: 0 })}`;
  }

  function setupPaymentInput(input) {
    input.addEventListener('focus', () => {
      if (parseFloat(input.value) === 0) {
        input.value = '';
      }
    });
    input.addEventListener('blur', () => {
      if (input.value.trim() === '' || isNaN(parseFloat(input.value))) {
        input.value = '0';
      }
    });
  }

  setupPaymentInput(paymentCashInput);
  setupPaymentInput(paymentCardInput);

  [paymentCashInput, paymentCardInput].forEach(input => {
    input.addEventListener('input', () => {
      updateCompleteButtonState();
      updateDifferenceDisplay(updateTotals());
    });
  });

  function updateCompleteButtonState() {
    const total = updateTotals();
    const paid = (parseFloat(paymentCashInput.value) || 0) + (parseFloat(paymentCardInput.value) || 0);
    completeSaleBtn.disabled = saleItems.length === 0 || paid < total;
  }

  completeSaleBtn.addEventListener('click', () => {
    if (saleItems.length === 0) return alert('Agrega productos a la venta.');
    const total = updateTotals();
    const cash = parseFloat(paymentCashInput.value) || 0;
    const card = parseFloat(paymentCardInput.value) || 0;
    const paid = cash + card;
    if (paid < total) return alert('El pago total no cubre el total de la venta.');

    const data = {
      invoice_number: invoiceNumberInput.value,
      customer_id: customerIdHidden.value || null,
      payment_breakdown: { efectivo: cash, tarjeta: card },
      notes: notesInput.value,
      items: saleItems.map(i => ({
        product_id: i.product_id,
        quantity: i.quantity,
        unit_price: i.unit_price,
        iva_type: i.iva_type
      }))
    };

    fetch('/sales/new', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
      .then(res => res.json())
      .then(resp => {
        if (resp.success) {
          completedInvoiceNumberSpan.textContent = resp.invoice_number;
          completedSaleIdSpan.textContent = resp.sale_id; // 👈 guardar ID de la venta
          successModal.show();
          resetForm();
        } else {
          alert('Error: ' + (resp.error || 'desconocido'));
        }
      })
      .catch(err => {
        alert('Error en la comunicación con el servidor.');
        console.error(err);
      });
  });

  document.getElementById('printInvoice').addEventListener('click', () => {
    const saleId = completedSaleIdSpan.textContent;
    if (saleId) window.open(`/facturacion/pdf/${saleId}`, '_blank');
  });

  function resetForm() {
    saleItems.length = 0;
    renderProductsTable();
    paymentCashInput.value = '0';
    paymentCardInput.value = '0';
    if (paymentDifferenceInput) paymentDifferenceInput.value = '';
    notesInput.value = '';
    customerRucInput.value = '';
    customerNameDisplay.textContent = '';
    customerIdHidden.value = '';
    updateCompleteButtonState();
    fetch('/api/next-invoice-number')
      .then(res => res.json())
      .then(data => {
        invoiceNumberInput.value = data.invoice_number || '001-001-0000001';
      });
  }

  function initializeSaleForm() {
    renderProductsTable();
    updateCompleteButtonState();
  }

  initializeSaleForm();
});
