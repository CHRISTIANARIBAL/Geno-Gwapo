from django.shortcuts import render, get_object_or_404, redirect
from .models import *
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from decimal import Decimal

# Home page - show all gamecocks
def home(request):
    products = Product.objects.all()
    return render(request, 'shop/home.html', {'products': products})

# Product detail page
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'shop/product_detail.html', {'product': product})

def user_login(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        # 🧾 REGISTER
        if action == 'register':
            username = request.POST['username']
            password = request.POST['password']
            confirm = request.POST['confirm']
            
            if password != confirm:
                messages.error(request, 'Passwords do not match.')
            elif User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists.')
            else:
                user = User.objects.create_user(username=username, password=password, is_customer=True)
                messages.success(request, 'Account created successfully! You can now log in.')

        # 🔐 LOGIN
        elif action == 'login':
            username = request.POST['username']
            password = request.POST['password']
            user = authenticate(request, username=username, password=password)

            if user is not None and user.is_customer:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, 'Invalid credentials or not a customer account.')

    return render(request, 'shop/user_login.html')

def admin_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_admin:
            login(request, user)
            return redirect('admin_dashboard')
        else:
            messages.error(request, 'Invalid credentials or not an admin account.')
    return render(request, 'shop/admin_login.html')

def user_logout(request):
    logout(request)
    return redirect('user_login')

def shop_view(request):
    products = Product.objects.all()
    return render(request, 'shop/shop.html', {'products': products})

def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart = request.session.get('cart', {})

    product_id = str(product.id)

    # If the product already exists in the cart, increase quantity
    if product_id in cart:
        cart[product_id]['quantity'] += 1
    else:
        # Add new product to cart
        cart[product_id] = {
            'name': product.name,
            'price': str(product.price),  # stored as string to be JSON serializable
            'quantity': 1,
            'image': product.image.url if product.image else '',
        }

    # Save back to session
    request.session['cart'] = cart
    request.session.modified = True

    return redirect('home')

def cart_view(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0.0

    for product_id, item in cart.items():
        try:
            price = float(item['price'])
            quantity = int(item['quantity'])
            subtotal = price * quantity
            total += subtotal
            cart_items.append({
                'id': product_id,
                'name': item['name'],
                'price': price,
                'quantity': quantity,
                'image': item['image'],
                'subtotal': subtotal,
            })
        except Exception as e:
            print("Cart error:", e)

    return render(request, 'shop/cart.html', {'cart_items': cart_items, 'total': total})


def update_cart(request):
    if request.method == "POST":
        cart = request.session.get('cart', {})
        action = request.POST.get('action', '')

        if action.startswith('increase_'):
            product_id = action.split('_')[1]
            if product_id in cart:
                cart[product_id]['quantity'] += 1

        elif action.startswith('decrease_'):
            product_id = action.split('_')[1]
            if product_id in cart:
                if cart[product_id]['quantity'] > 1:
                    cart[product_id]['quantity'] -= 1
                else:
                    # if quantity == 1 and user hits "−", remove item
                    cart.pop(product_id)

        request.session['cart'] = cart
        return redirect('cart')

    return redirect('cart')
@require_POST
def update_cart_quantity(request, product_id):
    cart = request.session.get('cart', {})
    action = request.POST.get('action')

    if str(product_id) in cart:
        if action == 'increase':
            cart[str(product_id)]['quantity'] += 1
        elif action == 'decrease':
            cart[str(product_id)]['quantity'] = max(1, cart[str(product_id)]['quantity'] - 1)

    request.session['cart'] = cart
    request.session.modified = True
    return redirect('cart')

import json
from django.db import transaction
@login_required
@transaction.atomic
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.warning(request, "Your cart is empty.")
        return redirect('cart')

    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_items')

        if not selected_ids:
            messages.error(request, "⚠️ Please select at least one product to checkout.")
            return redirect('checkout')

        # ✅ Convert both to string to ensure matching keys
        selected_cart = {str(pid): item for pid, item in cart.items() if str(pid) in selected_ids}

        if not selected_cart:
            messages.error(request, "⚠️ Selected products were not found in your cart.")
            return redirect('checkout')

        total = sum(Decimal(item['price']) * item['quantity'] for item in selected_cart.values())
        order = Order.objects.create(customer=request.user, total_price=total)

        for pid, item in selected_cart.items():
            product = get_object_or_404(Product, id=int(pid))
            if product.stock < item['quantity']:
                messages.error(request, f"⚠️ Not enough stock for {product.name}.")
                order.delete()
                return redirect('cart')

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item['quantity'],
                subtotal=Decimal(item['price']) * item['quantity']
            )

            product.stock -= item['quantity']
            product.save()

        # ✅ Remove only the checked-out items
        for pid in selected_ids:
            cart.pop(str(pid), None)

        request.session['cart'] = cart
        request.session.modified = True

        messages.success(request, "✅ Checkout successful! Your order has been placed.")
        return render(request, 'shop/checkout_success.html', {'order': order})

    total = sum(Decimal(item['price']) * item['quantity'] for item in cart.values())
    return render(request, 'shop/checkout.html', {'cart': cart, 'total': total})

@login_required
def checkout_view(request):
    cart = request.session.get('cart', {})

    if not cart:
        messages.warning(request, "Your cart is empty.")
        return redirect('cart')

    total = sum(Decimal(item['price']) * item['quantity'] for item in cart.values())

    if request.method == 'POST':
        # ✅ Create the order when Confirm Order is clicked
        order = Order.objects.create(customer=request.user, total_price=total)

        for product_id, item in cart.items():
            product = get_object_or_404(Product, id=product_id)

            # Stock validation
            if product.stock < item['quantity']:
                messages.error(request, f"⚠️ Not enough stock for {product.name}.")
                order.delete()
                return redirect('cart')

            # Create order item
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item['quantity'],
                subtotal=Decimal(item['price']) * item['quantity']
            )

            # Decrease stock
            product.stock -= item['quantity']
            product.save()

        # Clear cart session
        request.session['cart'] = {}
        request.session.modified = True

        messages.success(request, "✅ Your order has been successfully placed!")
        return render(request, 'shop/checkout_success.html', {'order': order})

    # ✅ Show checkout confirmation page
    return render(request, 'shop/checkout.html', {'cart': cart, 'total': total})

#/////////admin area//////////////////
@login_required(login_url='admin_login')
def admin_dashboard(request):
    if not request.user.is_admin:
        return redirect('home')

    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_orders = Order.objects.count()

    context = {
        'total_products': total_products,
        'total_categories': total_categories,
        'total_orders': total_orders,
    }

    return render(request, 'shop/myadmin/admin_dashboard.html', context)

@login_required(login_url='admin_login')
def admin_products(request):
    if not request.user.is_admin:
        return redirect('home')
    products = Product.objects.all()
    return render(request, 'shop/myadmin/products.html', {'products': products})

@login_required(login_url='admin_login')
def admin_add_product(request):
    if not request.user.is_admin:
        return redirect('home')

    categories = Category.objects.all()

    if request.method == 'POST':
        name = request.POST['name']
        description = request.POST['description']
        price = request.POST['price']
        stock = request.POST['stock']
        category_id = request.POST['category']
        image = request.FILES.get('image')

        category = get_object_or_404(Category, id=category_id)
        Product.objects.create(
            category=category,
            name=name,
            description=description,
            price=price,
            stock=stock,
            image=image
        )
        messages.success(request, "Product added successfully!")
        return redirect('admin_products')

    return render(request, 'shop/myadmin/add_product.html', {'categories': categories})

@login_required(login_url='admin_login')
def admin_edit_product(request, product_id):
    if not request.user.is_admin:
        return redirect('home')

    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.all()

    if request.method == 'POST':
        product.name = request.POST['name']
        product.description = request.POST['description']
        product.price = request.POST['price']
        product.stock = request.POST['stock']
        product.category = get_object_or_404(Category, id=request.POST['category'])
        if 'image' in request.FILES:
            product.image = request.FILES['image']
        product.save()
        messages.success(request, "Product updated successfully!")
        return redirect('admin_products')

    return render(request, 'shop/myadmin/edit_product.html', {'product': product, 'categories': categories})

@login_required(login_url='admin_login')
def admin_delete_product(request, product_id):
    if not request.user.is_admin:
        return redirect('home')

    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, "Product deleted successfully!")
    return redirect('admin_products')

@login_required(login_url='admin_login')
def admin_categories(request):
    if not request.user.is_admin:
        return redirect('home')

    categories = Category.objects.all()
    return render(request, 'shop/myadmin/categories.html', {'categories': categories})


@login_required(login_url='admin_login')
def admin_add_category(request):
    if not request.user.is_admin:
        return redirect('home')

    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Category.objects.create(name=name)
            messages.success(request, "✅ Category added successfully!")
            return redirect('admin_categories')
        else:
            messages.error(request, "⚠️ Category name cannot be empty.")

    return render(request, 'shop/myadmin/add_category.html')


@login_required(login_url='admin_login')
def admin_edit_category(request, category_id):
    if not request.user.is_admin:
        return redirect('home')

    category = get_object_or_404(Category, id=category_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            category.name = name
            category.save()
            messages.success(request, "✅ Category updated successfully!")
            return redirect('admin_categories')
        else:
            messages.error(request, "⚠️ Category name cannot be empty.")

    return render(request, 'shop/myadmin/edit_category.html', {'category': category})


@login_required(login_url='admin_login')
def admin_delete_category(request, category_id):
    if not request.user.is_admin:
        return redirect('home')

    category = get_object_or_404(Category, id=category_id)
    category.delete()
    messages.success(request, "🗑️ Category deleted successfully!")
    return redirect('admin_categories')


# ======================
# 📦 ORDER MANAGEMENT
# ======================
@login_required(login_url='admin_login')
def admin_orders(request):
    if not request.user.is_admin:
        return redirect('home')

    orders = Order.objects.all().select_related('customer').order_by('-created_at')
    return render(request, 'shop/myadmin/orders.html', {'orders': orders})