# POS-Kiosk
## Description
POS-System for a Kiosks in a School ore somthing like that.

This is a simple POS system for School-Kiosks or other thinks like that.

## Features:
- Student can with his barcode or NFC-Tag pay with his balance or with Cash.
- With your barcode or NFC-Tag you can add money, see your balance and see your last transactions.
- Seller Accounts
- Add Balance to a Student as Seller
- Transaction Log for the administration
- For Sellers a statistics of all her sells
- Simple Kiosk UI for the Seller
- A simple UI for the Student
- Admins can easy edit the products and the categories

## Inforation:
Default Admin Account:
- Username: admin
- Password: password


## All Urls:
### Seller:
- `/kiosk`
- `/add_money`
- `/checkout`

### Student Station (One PC in the Kiosk to use for the Students):
- `/student`
- `/student/options/<int:id>`

### Administration:
- `/dashboard`
- `/admin_dashboard`
- `/update_user`
- `/add_seller`
- `/student/list`
- `/student/add`
- `/product/add`
- `/product/list`
