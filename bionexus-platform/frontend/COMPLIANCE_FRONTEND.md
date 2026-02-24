# BioNexus Compliance Frontend

## Overview

Frontend for GxP-compliant parsing validation and certification workflow. Implements 21 CFR Part 11 requirements through the UI.

## Architecture

### Components

#### ParsingValidationComponent
**Split-view validation interface**
- Left: Raw file viewer (PDF/CSV)
- Right: Dynamic validation form
- Real-time chain integrity badge
- Correction tracking
- Certification modal

#### DynamicFormBuilder
**Auto-generated form from Pydantic schema**
- Field grouping (basic, equipment, samples)
- Visual distinction: Green (AI) vs Yellow (corrected)
- Inline edit with reason documentation
- Live JSON validation
- 21 CFR Part 11 compliance warnings

#### ChainIntegrityBadge
**Real-time audit chain verification**
- Calls `verify_chain_integrity()` API
- Auto-refresh every 30 seconds
- Shows corrupted record details
- Safe-to-export indicator
- Prevents certification if chain compromised

#### CorrectionTracker
**Documents human corrections**
- Displays all field modifications
- Original vs corrected values
- Reason for each correction
- Audit trail integration

#### RawFileViewer
**Display original machine files**
- PDF viewer (iframe)
- CSV table viewer
- Text/plain viewer
- Download capability
- Hash verification badge

#### CertificationModal
**Double authentication certification**
- Step 1: Password re-entry
- Step 2: Certification notes
- Step 3: Review & confirm
- Non-repudiable signature
- Timestamp attribution

### Services

#### parsingService.ts
```typescript
getParsedData(id)           // Get ParsedData for validation
validateParsing(id, data)   // Submit corrections
getRawFile(id)              // Download original file
getCorrectionHistory(id)    // Get audit trail of corrections
```

#### integrityService.ts
```typescript
checkChainIntegrity()       // Verify audit chain (real-time)
isSafeToExport()           // Quick check for export eligibility
getCorruptionReport()      // Detailed corruption report
clearCache()               // Force API refresh
```

#### cryptoService.ts
```typescript
signReport(request)        // Certify with double auth
getAccessToken()           // JWT token management
refreshToken()             // Token rotation
verifyPassword()           // Password verification
verifyOTP()               // OTP verification
verifySignature()         // Signature validation
```

## 21 CFR Part 11 Features

### 1. Attributability
✓ Every correction attributed to user + timestamp
✓ Certification requires password re-entry
✓ Non-repudiable signing in audit trail

### 2. Legibility
✓ Human-readable forms with clear labels
✓ Visual distinction between AI and human corrections
✓ Structured correction notes

### 3. Contemporaneous
✓ Timestamps recorded for all actions
✓ Chain integrity check timestamp
✓ Certification timestamp immutable

### 4. Original
✓ Raw file viewer shows original machine output
✓ File hash verification
✓ No modification of source data

### 5. Accurate
✓ Pydantic schema validation
✓ Type checking for all fields
✓ Live validation warnings

### 6. Complete
✓ All corrections documented with reason
✓ Audit chain verification before export
✓ No skipped validations allowed

### 7. Consistent
✓ Standardized form layout
✓ Consistent correction tracking
✓ Uniform certification process

### 8. Enduring
✓ All data in audit trail (soft delete only)
✓ Correction history preserved
✓ Chain integrity checks recorded

### 9. Available
✓ Real-time chain integrity status
✓ API-driven data loading
✓ Cache management for performance

## Component Usage

### Basic Setup

```typescript
import ParsingValidationComponent from './components/ParsingValidation/ParsingValidationComponent';

export default function App() {
  return (
    <ParsingValidationComponent
      parsedDataId={123}
      onValidationComplete={() => console.log('Done!')}
    />
  );
}
```

### With Integrity Badge

```typescript
import ChainIntegrityBadge from './components/ParsingValidation/ChainIntegrityBadge';

// In your header/toolbar
<ChainIntegrityBadge
  autoRefresh={true}
  refreshInterval={30000}
/>
```

## API Integration

### Backend Endpoints Required

```
GET  /api/parsing/{id}/                 - Get ParsedData
POST /api/parsing/{id}/validate/        - Validate & submit
GET  /api/parsing/{id}/corrections/     - Get correction history
GET  /api/parsing/{id}/rawfile/         - Download raw file
GET  /api/integrity/check/              - Check chain integrity
POST /api/reports/{id}/sign/            - Certify with double auth
```

See `core/api_views.py` for implementation.

## Features

### ✓ Real-Time Validation
- Live JSON validation as user types
- Visual feedback for errors
- Type checking against schema

### ✓ Correction Tracking
- Every field change tracked
- Reason documentation required
- Audit trail integration

### ✓ Chain Integrity
- Automatic verification
- Corruption detection
- Export prevention if compromised

### ✓ Double Authentication
- Password re-entry required
- Optional OTP support
- Non-repudiable signature

### ✓ Split View
- Original file on left
- Form on right
- Side-by-side comparison

### ✓ Dark Mode Ready
- Tailwind CSS classes
- Accessible color contrasts
- Theme support

## Performance

### Caching
- Chain integrity: 5-second cache
- Parsed data: Loaded once
- Session storage for status

### Optimization
- Lazy component loading
- Memoized form fields
- Debounced API calls
- Image optimization

## Security

### Client-Side
✓ JWT token management
✓ Password hashing (server-side)
✓ XSS protection via React
✓ CSRF tokens in all POST requests

### Server-Side (Backend)
✓ Password verification before signing
✓ Permission checks on all endpoints
✓ Audit trail immutability
✓ Chain integrity verification

## Testing

### Unit Tests (Jest)
```typescript
test('CorrectionTracker displays corrections', () => {
  const corrections = [
    { field: 'name', original: 'A', corrected: 'B', notes: 'Test' }
  ];
  render(<CorrectionTracker corrections={corrections} />);
  expect(screen.getByText('1 Correction')).toBeInTheDocument();
});
```

### Integration Tests
- Form submission flow
- Chain integrity API calls
- Certification signing process
- Error handling

### E2E Tests (Cypress)
```typescript
describe('Parsing Validation', () => {
  it('should validate and certify a parsing', () => {
    cy.visit('/parsing/123');
    cy.get('[data-testid="form-field"]').type('corrected value');
    cy.get('[data-testid="notes"]').type('Fixed typo');
    cy.get('[data-testid="validate"]').click();
    cy.get('[data-testid="certify"]').click();
    cy.get('[data-testid="password"]').type('password');
    cy.get('[data-testid="confirm"]').click();
    cy.contains('Certified').should('be.visible');
  });
});
```

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Accessibility

- WCAG 2.1 AA compliant
- Keyboard navigation support
- Screen reader friendly
- Color contrast verified
- Focus indicators

## Localization

Configure in `public/locales/`:
- English (en)
- French (fr)
- German (de)
- Spanish (es)

## Environment Variables

```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_ENV=development
REACT_APP_FEATURE_2FA=false
REACT_APP_LOG_LEVEL=info
```

## Deployment

### Development
```bash
npm install
npm start
```

### Production
```bash
npm run build
npm run serve
```

### Docker
```dockerfile
FROM node:16-alpine AS build
WORKDIR /app
COPY . .
RUN npm install && npm run build

FROM node:16-alpine
WORKDIR /app
COPY --from=build /app/build ./public
CMD ["serve", "-s", "public"]
```

## Troubleshooting

### Chain Integrity Badge not updating
- Check `API_BASE_URL` in config
- Verify backend API is running
- Check browser console for errors
- Clear cache: `integrityService.clearCache()`

### Form not validating
- Check Pydantic schema matches
- Verify field names are correct
- Check browser console for validation errors
- Ensure JSON is valid

### Certification fails
- Check password is correct
- Verify chain integrity is OK
- Check 2FA is enabled (if required)
- Review backend logs

## License

Same as BioNexus project
