#!/usr/bin/env bash

# Frontend Auth Integration Test Script
# This script helps verify that all frontend components are using auth utilities correctly

echo "🧪 Zelda AI Assistant - Frontend Auth Integration Test"
echo "=" * 60

# Test 1: Check if auth utility file exists and has required exports
echo "📋 Test 1: Checking auth utility exports..."
if [ -f "src/utils/auth.js" ]; then
    echo "✅ Auth utility file exists"
    
    required_exports=("validateToken" "getAuthHeader" "makeAuthenticatedRequest" "isAuthenticated" "logout")
    
    for export in "${required_exports[@]}"; do
        if grep -q "export.*$export" src/utils/auth.js; then
            echo "✅ $export function exported"
        else
            echo "❌ $export function missing"
        fi
    done
else
    echo "❌ Auth utility file missing"
fi

# Test 2: Check if components are importing auth utilities
echo -e "\n📋 Test 2: Checking component imports..."
components=("components/VoiceAssistant.jsx" "context/AuthContext.jsx" "services/api.js")

for component in "${components[@]}"; do
    if [ -f "src/$component" ]; then
        if grep -q "from.*utils/auth" "src/$component"; then
            echo "✅ $component imports auth utilities"
        else
            echo "❌ $component missing auth utility imports"
        fi
    else
        echo "⚠️  $component not found"
    fi
done

# Test 3: Check for consistent token key usage
echo -e "\n📋 Test 3: Checking for consistent token storage..."
if grep -r "authToken" src/ --include="*.jsx" --include="*.js" | grep -v node_modules; then
    echo "⚠️  Found 'authToken' usage - should be 'token'"
else
    echo "✅ Consistent 'token' key usage"
fi

# Test 4: Check for direct localStorage token access
echo -e "\n📋 Test 4: Checking for direct localStorage access patterns..."
direct_access=$(grep -r "localStorage.getItem('token')" src/ --include="*.jsx" | grep -v "auth.js" | grep -v "AuthContext.jsx")
if [ -n "$direct_access" ]; then
    echo "⚠️  Found direct localStorage access (consider using auth utilities):"
    echo "$direct_access"
else
    echo "✅ No problematic direct localStorage access found"
fi

# Test 5: Check for direct fetch calls that should use auth utilities
echo -e "\n📋 Test 5: Checking for direct fetch calls..."
direct_fetch=$(grep -r "fetch.*headers.*Authorization" src/ --include="*.jsx" | grep -v "makeAuthenticatedRequest")
if [ -n "$direct_fetch" ]; then
    echo "⚠️  Found direct fetch with Authorization headers:"
    echo "$direct_fetch"
else
    echo "✅ No direct fetch calls with auth headers found"
fi

echo -e "\n" + "=" * 60
echo "📊 Frontend Auth Integration Test Complete"
echo "=" * 60

echo -e "\n🎯 Next Steps:"
echo "1. Start the frontend: npm run dev"
echo "2. Test login/logout functionality"
echo "3. Test voice assistant authentication"
echo "4. Verify all API calls include proper authentication"
echo -e "\n💡 If any tests failed, review the specific files mentioned above."