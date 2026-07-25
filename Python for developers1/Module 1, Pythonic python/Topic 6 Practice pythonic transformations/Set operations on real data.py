online_order = {'trail_running_shoes', 'hydration_pack', 'compression_socks', 'baseball_cap', 'yoga_mat'}
instore_order_returns = { 'baseball_cap', 'yoga_mat', 'bike_lights', 'tail_wind_spray', 'hydration_pack'}
ordersin_both = online_order.intersection(instore_order_returns)
combined_orders = online_order.union(instore_order_returns)
instore_order_results_only = online_order.difference(instore_order_returns)
print(f"All items across all channels: {combined_orders}")
print(f"Items in both online orders and store returns: {ordersin_both}")
print(f"Items only purchased online (not in return): {instore_order_results_only}")