-- Fictional orders; all money values are USD cents.
CREATE OR REPLACE TEMP TABLE orders (
  order_id VARCHAR, destination VARCHAR, weight_g BIGINT,
  revenue_cents BIGINT, product_cost_cents BIGINT
);
INSERT INTO orders VALUES
  ('A-101', 'US',  500, 3500, 1800),
  ('A-102', 'US', 1800, 2400, 1600),
  ('A-103', 'CA', 1200, 4000, 2600),
  ('A-104', 'GB',  700, 6000, 2800),
  ('A-105', 'AU',  900, 3000, 1400);
