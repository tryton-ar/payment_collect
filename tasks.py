# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from trytond.transaction import Transaction

def post_invoices_execution(collect_id, user_id=None):
    'Post Invoices passed by parameters'
    pool = Pool()
    User = pool.get('res.user')
    Invoice = pool.get('account.invoice')
    Collect = pool.get('payment.collect')
    invoices = []

    if not user_id:
        user, = User.search([
                ('login', '=', 'admin'),
                ])
        user_id = user.id

    with Transaction().set_user(user_id), Transaction().set_context(
            User.get_preferences(context_only=True)):
        collect = Collect(collect_id)
        for transaction in collect.transactions_accepted:
            invoices.append(transaction.invoice)
        Invoice.post(invoices)
