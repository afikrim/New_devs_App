/**
 * Money formatting that operates on decimal strings, never JS floats.
 *
 * Revenue is transported from the backend as a decimal string (e.g. "2250.000"
 * or "333.334"). Parsing it into a JS number would reintroduce binary
 * floating-point error, so these helpers work on the string directly.
 */

/** Increment a non-negative integer string by 1, handling carry ("999" -> "1000"). */
function incrementIntegerString(digits: string): string {
  const arr = digits.split('');
  for (let i = arr.length - 1; i >= 0; i--) {
    if (arr[i] === '9') {
      arr[i] = '0';
    } else {
      arr[i] = String(Number(arr[i]) + 1);
      return arr.join('');
    }
  }
  return '1' + arr.join('');
}

/** Insert thousands separators into a non-negative integer string. */
function groupThousands(digits: string): string {
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/**
 * Format a decimal string as a money amount with grouped thousands and a
 * fixed number of fraction digits (default 2), rounding half-up. Returns the
 * formatted number only (no currency symbol).
 */
export function formatMoney(value: string | number, fractionDigits = 2): string {
  const raw = (typeof value === 'number' ? value.toString() : value ?? '').trim();
  if (raw === '') return (0).toFixed(fractionDigits);

  const negative = raw.startsWith('-');
  const unsigned = negative ? raw.slice(1) : raw;

  const [intPartRaw = '0', fracPartRaw = ''] = unsigned.split('.');
  let intDigits = intPartRaw.replace(/\D/g, '') || '0';

  // Keep one extra fraction digit to decide rounding, padded so it always exists.
  const padded = (fracPartRaw + '0'.repeat(fractionDigits + 1)).slice(0, fractionDigits + 1);
  let kept = padded.slice(0, fractionDigits);
  const rounder = Number(padded[fractionDigits] || '0');

  if (rounder >= 5) {
    if (kept === '') {
      // No fraction digits requested; carry straight into the integer part.
      intDigits = incrementIntegerString(intDigits);
    } else {
      const bumped = (Number(kept) + 1).toString().padStart(fractionDigits, '0');
      if (bumped.length > fractionDigits) {
        // e.g. "99" -> "100": the leading 1 carries into the integer part.
        intDigits = incrementIntegerString(intDigits);
        kept = bumped.slice(1);
      } else {
        kept = bumped;
      }
    }
  }

  // Drop a leading-zero artifact like "007" -> "7" while keeping a single "0".
  intDigits = intDigits.replace(/^0+(?=\d)/, '');

  const grouped = groupThousands(intDigits);
  const formatted = fractionDigits > 0 ? `${grouped}.${kept}` : grouped;
  return negative && formatted.replace(/[.,]/g, '').replace(/0/g, '') !== '' ? `-${formatted}` : formatted;
}
