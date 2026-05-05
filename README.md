# FabVibe — E-Commerce Platform

A full-featured Django e-commerce platform for clothing, built with a custom admin panel, virtual try-on, wallet system, and order management.

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

- Frontend: http://localhost:8000/
- Admin Panel: http://localhost:8000/admin-panel/

---

## 🏗️ Project Structure

| App | Purpose |
|---|---|
| `users` | Custom auth, OTP login, profile & addresses |
| `products` | Catalog, categories, inventory, wishlist, reviews |
| `cart` | Shopping cart with coupon support |
| `orders` | Checkout, order tracking, returns & exchanges |
| `wallet` | In-app wallet with credit/debit transactions |
| `admin_panel` | Custom dashboard for managing the store |

---

## ✨ Features Built

### User System
- Custom user model with email/phone login
- OTP-based verification (email & SMS)
- Profile with body measurements for size recommendations
- Multiple saved addresses
- Password complexity validation

### Product Catalog
- 80+ products across 4 categories (Men, Women, Kids, Accessories)
- 16 subcategories with images
- Product sizes, colors, and per-size inventory tracking
- Product reviews & ratings
- Wishlist
- Recently viewed products
- Stock alerts (notify when back in stock)
- Homepage banners

### Shopping Cart
- Add/remove items with size selection
- Coupon code support
- Cart persists for logged-in users

### Orders
- Checkout with multiple payment methods: COD, UPI, Card (Razorpay)
- Wallet split payment (pay part from wallet, rest via gateway)
- Order status tracking: Pending → Processing → Shipped → Out for Delivery → Delivered
- OTP-based delivery verification
- Return & exchange requests (within 7 days)
- Invoice generation
- Email notifications via Brevo (Sendinblue)

### Wallet
- Auto-credited on order cancellations and approved returns
- Full transaction history with balance tracking
- Can be used partially or fully at checkout

### Virtual Try-On
- Upload a photo and try on clothing virtually (AI-powered via Hugging Face IDM-VTON)
- Try-on history saved per user
- AR try-on for accessories (sunglasses)

### Admin Panel (Custom)
- Dashboard with sales metrics
- Product & category management with image upload
- Order management with status updates and location tracking
- Inventory management with low-stock alerts and logs
- User management
- Banner management
- Return & exchange approval workflow
- Celery-based async tasks (order emails, stock notifications)

---

## 🛠️ Tech Stack

- **Backend:** Django 4.x, Python 3.11
- **Database:** SQLite3 (development)
- **Async Tasks:** Celery with filesystem broker
- **Payments:** Razorpay
- **Email:** Brevo (Sendinblue) transactional API
- **SMS/WhatsApp:** Twilio / Fast2SMS / WhatsApp API
- **AI Try-On:** Hugging Face IDM-VTON (ZeroGPU)
- **Frontend:** Bootstrap 4, custom CSS/JS

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and fill in:

```env
SECRET_KEY=your-secret-key
DEBUG=True
EMAIL_HOST_USER=your-email
BREVO_API_KEY=your-brevo-key
RAZORPAY_KEY_ID=your-razorpay-key
RAZORPAY_KEY_SECRET=your-razorpay-secret
HF_TOKEN=your-huggingface-token
TWILIO_ACCOUNT_SID=your-twilio-sid
```

---

## 📸 Screenshots

| Page | Preview |
|---|---|
| Login | ![](./images/LoginPage.png) |
| Register | ![](./images/RegisterPage.png) |
| Home | ![](./images\HomePage.png) |
| Dashboard | ![](./images/dashboard.png) |
| Category | ![](./images/category.png) |
| Category (Sunglasses) | ![](./images/category_sunglasses.png) |
| Product | ![](./images/product.png) |
| Virtual Try-On | ![](./images/feature_virtual-tryON.png) |
| Payment | ![](./images/payment.png) |
| Order Management | ![](./images/order_management.png) |
| Shipping | ![](./images/shipping.png) |
| Stock | ![](./images/stock.png) |
| Update Location | ![](./images/update_location.png) |

---

## 📝 License

Proprietary — FabVibe E-Commerce Platform  
**Version:** 1.0.0
