def evaluate_heavy_lift(*args, weights_collection=None):
    if weights_collection is None:
        weights_collection = []
    
    weights_collection.extend(filter(lambda w: w > 50.0, args))
    
    return sum(weights_collection)

custom_batch = [20.0]
print(evaluate_heavy_lift(45.0, 55.0, 65.0, weights_collection=custom_batch))
print(evaluate_heavy_lift(40.0, 52.0, 80.0))