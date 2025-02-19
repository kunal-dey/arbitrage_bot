from decimal import Decimal, ROUND_DOWN


def find_best_amount(inr_based_pair_value, non_inr_based_pair_value,
                     precision_inr=2, precision_non_inr=5,
                     min_amount=900, max_amount=1000, step=0.01,
                     min_possible_inr_pair_quantity=0, min_possible_non_inr_pair_quantity=0):
    """
    Finds an optimized amount that minimizes the leftover precision error.
    Starts searching from max_amount and decreases step-wise to find an optimal solution faster.
    The search **terminates early** when the possible amount goes below the required minimum.

    Args:
        inr_based_pair_value (float): The value of the INR-based pair.
        non_inr_based_pair_value (float): The value of the non-INR-based pair.
        precision_inr (int): Number of decimal places for inr_based_pair_quantity.
        precision_non_inr (int): Number of decimal places for non_inr_based_pair_quantity.
        min_amount (float): Minimum amount to start searching from.
        max_amount (float): Maximum amount to search up to.
        step (float): Decrement step for the amount.
        min_possible_inr_pair_quantity (float): Minimum possible INR-based pair quantity.
        min_possible_non_inr_pair_quantity (float): Minimum possible non-INR-based pair quantity.

    Returns:
        float: Optimized amount with minimum precision loss or the last valid amount before search termination.
    """
    min_amount = Decimal(str(min_amount))
    max_amount = Decimal(str(max_amount))
    step = Decimal(str(step))

    # Define Decimal precision formats
    precision_inr_format = Decimal("1." + "0" * precision_inr)  # Example: 0.01 for precision_inr = 2
    precision_non_inr_format = Decimal("1." + "0" * precision_non_inr)  # Example: 0.00001 for precision_non_inr = 5

    best_amount = None
    min_error = float("inf")

    amount = max_amount  # Start from the maximum amount
    while amount >= min_amount:
        # Calculate exact values before rounding
        exact_inr_based_pair_quantity = amount / Decimal(str(inr_based_pair_value))
        exact_non_inr_based_pair_quantity = exact_inr_based_pair_quantity / Decimal(str(non_inr_based_pair_value))

        # If we go below the allowed minimum, **terminate search immediately**
        if exact_inr_based_pair_quantity < Decimal(str(min_possible_inr_pair_quantity)) or \
                exact_non_inr_based_pair_quantity < Decimal(str(min_possible_non_inr_pair_quantity)):
            break  # Stop searching, return the last valid best amount

        # Round to defined precision
        rounded_inr_based_pair_quantity = exact_inr_based_pair_quantity.quantize(precision_inr_format,
                                                                                 rounding=ROUND_DOWN)
        rounded_non_inr_based_pair_quantity = exact_non_inr_based_pair_quantity.quantize(precision_non_inr_format,
                                                                                         rounding=ROUND_DOWN)

        # Compute the precision error
        error_inr = abs(exact_inr_based_pair_quantity - rounded_inr_based_pair_quantity)
        error_non_inr = abs(exact_non_inr_based_pair_quantity - rounded_non_inr_based_pair_quantity)
        total_error = error_inr + error_non_inr

        # If total error is 0, return immediately (best possible match)
        if total_error == 0:
            return float(amount)

        # Update the best amount if the error is minimized
        if total_error < min_error:
            min_error = total_error
            best_amount = amount

        amount -= step  # Decrement amount

    return float(best_amount) if best_amount else None  # Return last valid amount
