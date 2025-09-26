#!/usr/bin/env python3
"""
Utility script to load RFPs into the database and test semantic similarity
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from semantic_service import SemanticService
import json

def main():
    print("🚀 Starting RFP loading and semantic similarity system...")

    # Initialize semantic service
    service = SemanticService()

    print("\n📊 Testing basic semantic similarity...")
    # Test basic similarity
    text1 = "technology workforce development training program"
    text2 = "STEM education and job training initiative"
    text3 = "environmental conservation project"

    similarity1 = service.calculate_semantic_similarity(text1, text2)
    similarity2 = service.calculate_semantic_similarity(text1, text3)

    print(f"Similarity: '{text1}' vs '{text2}': {similarity1:.3f}")
    print(f"Similarity: '{text1}' vs '{text3}': {similarity2:.3f}")

    print("\n📁 Loading RFPs from directory...")
    # Load RFPs
    rfps = service.load_rfps_from_directory()

    if rfps:
        print(f"✅ Successfully loaded {len(rfps)} RFPs")

        # Show sample RFP
        if rfps:
            sample = rfps[0]
            print(f"\n📄 Sample RFP:")
            print(f"Title: {sample['title']}")
            print(f"Category: {sample['category']}")
            print(f"Content preview: {sample['content'][:200]}...")

        print("\n💾 Storing RFPs in Supabase...")
        # Store in Supabase
        success = service.store_rfps_in_supabase(rfps)

        if success:
            print("✅ Successfully stored RFPs in Supabase")

            print("\n🔍 Testing semantic search...")
            # Test semantic search
            test_query = "technology workforce development program for underserved communities"
            similar_rfps = service.find_similar_rfps(test_query, limit=3)

            print(f"Query: '{test_query}'")
            print(f"Found {len(similar_rfps)} similar RFPs:")

            for i, rfp in enumerate(similar_rfps):
                score = rfp.get('similarity_score', rfp.get('similarity', 0))
                print(f"{i+1}. {rfp.get('title', 'Unknown')} (Similarity: {score:.3f})")

            # Test enhanced match scoring
            print("\n📈 Testing enhanced match scoring...")
            test_grant = {
                'title': 'Department of Labor Technology Workforce Development Grant',
                'description': 'Federal funding for technology training programs targeting underrepresented communities with job placement support',
                'amount': 500000,
                'funder': 'U.S. Department of Labor'
            }

            enhanced_score = service.calculate_enhanced_match_score(test_grant, similar_rfps)
            print(f"Enhanced match score for test grant: {enhanced_score}%")

        else:
            print("❌ Failed to store RFPs in Supabase")
    else:
        print("❌ No RFPs found to load")

    print("\n🎉 RFP loading and testing complete!")

if __name__ == "__main__":
    main()