from rest_framework import generics, status
from rest_framework.response import Response

from .models import Node
from .serializers import NodeSerializer
from rest_framework.permissions import IsAuthenticated  # adjust permission as needed

class NodeListCreateAPIView(generics.ListCreateAPIView):
    """
    GET: List all nodes.
    POST: Add a new node to share with.
    """
    queryset = Node.objects.all()
    serializer_class = NodeSerializer
    permission_classes = [IsAuthenticated]

class NodeRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET: Retrieve a single node.
    PUT/PATCH: Update node details (e.g., disable a node).
    DELETE: Remove a node to stop sharing with it.
    """
    queryset = Node.objects.all()
    serializer_class = NodeSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = NodeSerializer(data=request.data)
        if serializer.is_valid():
            node = serializer.save()
            return Response(NodeSerializer(node).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)