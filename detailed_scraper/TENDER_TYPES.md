# Tender Types Reference

This document lists all possible tender types that can appear in the system.

## Standard Tender Types

| Code | Full Name (Georgian) | English Translation |
|------|----------------------|---------------------|
| **NAT** | ელექტრონული ტენდერი აუქციონის გარეშე | Electronic tender without auction |
| **SPA** | ელექტრონული ტენდერი რევერსული აუქციონით | Electronic tender with reverse auction |
| **CON** | კონსოლიდირებული ტენდერი | Consolidated tender |
| **CNT** | კონკურსი | Competition/Contest |
| **MEP** | ორეტაპიანი ელექტრონული ტენდერი | Two-stage electronic tender |
| **DAP** | ელექტრონული ტენდერი განსხვავებული წესით | Electronic tender with different rules |
| **TEP** | ელექტრონული ტენდერი პრეკვალიფიკაციით | Electronic tender with pre-qualification |
| **GEO** | შესყიდვის ელექტრონული პროცედურა | Electronic procurement procedure |
| **DEP** | შესყიდვის ელ. პროცედურა დონორის სახსრებით | Electronic procurement procedure with donor funds |
| **GRA** | საგრანტო კონკურსი | Grant competition |
| **PPP** | საჯარო-კერძო თანამშრომლობა/კონცესია | Public-private partnership/concession |
| **B2B** | კერძო შესყიდვა | Private procurement |

## Simplified Tender Types

Some tender types have "simplified" (გამარტივებული) versions:

| Code | Full Name (Georgian) | English Translation |
|------|----------------------|---------------------|
| **NAT** | გამარტივებული ელექტრონული ტენდერი აუქციონის გარეშე | Simplified electronic tender without auction |
| **SPA** | გამარტივებული ელექტრონული ტენდერი რევერსული აუქციონით | Simplified electronic tender with reverse auction |
| **MEP** | ორეტაპიანი გამარტივებული ელექტრონული ტენდერი | Two-stage simplified electronic tender |
| **DAP** | გამარტივებული ელექტრონული ტენდერი განსხვავებული წესით | Simplified electronic tender with different rules |

## Notes

- The tender type code is extracted from the tender number (first 2-4 uppercase letters)
- The same code (e.g., NAT, SPA) can represent both standard and simplified versions
- The full description in Georgian text distinguishes between standard and simplified versions
- The parser maps both the code and full description to ensure accurate extraction

## Parser Behavior

The parser:
1. Extracts the code from the tender number (e.g., "NAT250020517" → "NAT")
2. Extracts the full description from the page text
3. Maps the full description to the appropriate code
4. Stores the code in `tender_type` field for consistency

